# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from calendar import monthrange
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError
import requests
import json
from ast import literal_eval


class BukIntegrationWizard(models.Model):
    _name = 'buk.integration.wizard'

    month = fields.Selection([("1", 'Enero'), ("2", 'Febrero'), ("3", 'Marzo'), ("4", 'Abril'),
                              ("5", 'Mayo'), ("6", 'Junio'), ("7", 'Julio'), ("8", 'Agosto'),
                              ("9", 'Septiembre'), ("10", 'Octubre'), ("11", 'Noviembre'), ("12", 'Diciembre'), ],
                             string='Mes', default=str(datetime.now().month))
    year = fields.Integer(min="2000", max="2100", string='Año', default=datetime.now().year)
    move_id = fields.Many2one('account.move', string="Asiento")
    # Flag para mostrar mensaje de sobreescribir, depende de este campo que se vea el mensaje
    moves_found = fields.Boolean(default=False, string="Asientos encontrados")
    # Flag de confirmación de sobreescribir
    confirmation = fields.Boolean('Ya existe un asiento contable importado para este periodo, ¿desea sobrescribir?', default=False)
    # Mensaje con resultado
    message = fields.Html('Resultado')
    state = fields.Selection([
        ('cancel', 'Cancelado'),
        ('done', 'Finalizado')
         ], string="Estado", default="cancel")

    @api.onchange('month', 'year')
    def confirmation_default(self):
        # Si se cambia el mes o año se vuelven los campos a por defecto
        if self.moves_found:
            self.message = ''
            self.confirmation = False
            self.moves_found = False
            return {
                'name': 'Importar asiento centralización de BUK',
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'buk.integration.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',

            }

    def refresh(self, message="", moves_found=False, confirmation=False):
        self.message = message
        self.moves_found = moves_found
        self.confirmation = confirmation
        return {
            'name': 'Importar asiento centralización de BUK',
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'buk.integration.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }

    @api.model
    def check_found(self, month, year):
        import_found = self.search([('month', '=', month), ('year', '=', year), ('state', '=', 'done')])
        if import_found and import_found.move_id:
            return import_found
        else:
            return None



    def start_integration(self):
        log = []

        if not self.year or self.year < 1900 or self.year > datetime.now().year:
            return self.refresh('<strong style="color:red">Ingrese un año válido</strong>')

        # first_day = datetime.strptime(str(self.month) + '-' + str(self.year), "%m-%Y")
        last_day = datetime.strptime("%s-%s-%s" % (monthrange(self.year, int(self.month))[1], int(self.month), self.year), "%d-%m-%Y")

        settings = self.env['ir.config_parameter'].sudo()
        buk_journal = settings.get_param('buk.buk_journal_id')
        create_partner = settings.get_param('buk.buk_create_partner', default=False)
        if buk_journal:
            # Si se encontraron asientos muestra mensaje sobreescribir:
            move_dict = {

                'date': last_day,
                'journal_id': int(buk_journal),
                'ref': 'Centralización %s/%s' % (self.month, self.year),

            }
        else:
            return self.refresh('<strong style="color:red">No hay nigún diario seleccionado. </strong><br/>Debe seleccionar un diario en Ajustes -> Facturando/Contabilidad -> Centralización </strong> ')

        import_found = self.check_found(int(self.month),self.year)
        if not import_found:
            move_created = self.env['account.move'].sudo().create(move_dict)
        else:
            # Si se no se confirma la ventana no hace nada
            if not self.confirmation:
                return self.refresh('', True)
            move_created = import_found.move_id
            move_created.line_ids = [(5, 0, 0)]
            import_found.state = "cancel"


        # Crea el objeto account move


            # import_found.sudo().unlink()

        # Se llama a la api de integración
        try:

            url = "https://personasfn-test.buk.cl/api/v1/chile/accounting/export"
            data = {
                'month': int(self.month),
                'year': self.year
            }
            headers = {
                'auth_token': 'EbZN2xTsY7iNzLpZJ911iMLb'
            }

            r = requests.get(url=url, data=data, headers=headers)
            if r.status_code == 201:
                result = r.json()
            elif r.status_code == 404:
                result = r.json()
                return self.refresh('<strong style="color:red"> %s </strong>' % result['errors'][0].capitalize())
            elif r.status_code == 401:
                return self.refresh('<strong style="color:red">Error: No autorizado</strong>')
            else:
                return self.refresh('<strong style="color:red">Error en integración</strong>')

        except ConnectionError as e:
            return self.refresh('<strong style="color:red">Error en integración</strong>')
        except ValueError as e:
            return self.refresh('<strong style="color:red">Error en integración</strong>')



        # Se crean los contenedores de ruts y cuentas con errores
        rut_error_log = []
        acc_error_log = []
        aaa_error_log = []

        # Si se encuentra rut
        for rut in result['data']:
            if result['data'][rut].__len__() > 0:
                for line in result['data'][rut]:
                    rut_f = line['cod_aux']

                    if line['cuenta']:
                        rut_partner = self.env['res.partner'].search([('vat', '=', rut_f.upper())], limit=1)
                        if not rut_partner and line['cod_aux'] != "":
                            if '<ul>%s</ul>' % line['cod_aux'] not in rut_error_log and not literal_eval(create_partner):
                                rut_error_log.append('<ul>%s</ul>' % line['cod_aux'])
                            else:
                                created_partner = self.env['res.partner'].create({
                                    'name': line['detalle'],
                                    'vat': rut_f.upper(),

                                })

                        acc = self.env['account.account'].search([('code', '=', line['cuenta'])], limit=1)
                        if not acc:
                            if '<ul>%s - %s</ul>' % (line['cuenta'], line['nombre_cuenta']) not in acc_error_log:
                                acc_error_log.append('<ul>%s - %s</ul>' % (line['cuenta'], line['nombre_cuenta']))
                        else:
                            aaa = self.env['account.analytic.account'].search([('buk_code', '=', line['cenco'])], limit=1)
                            aat = self.env['account.analytic.tag'].search([('buk_code', '=', line['cenco']), ('active_analytic_distribution', '=', True)], limit=1)

                            # Validación para que filtre etiquetas contables también
                            if not aaa and line['cenco'] != "" and not aat:
                                if '<ul>%s</ul>' % line['cenco'] not in aaa_error_log:
                                    aaa_error_log.append('<ul>%s</ul>' % line['cenco'])

                            line_created = self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'move_id': move_created.id,
                                'account_id': acc.id,
                                'partner_id': rut_partner.id,
                                'analytic_account_id': aaa.id or None,
                                'name': line['detalle'],
                                'debit': line['monto_debe'],
                                'credit': line['monto_haber'],
                            })
                            if aat and not aaa:
                                line_created.analytic_tag_ids = [(4, aat.id)]
                    else:
                        if '<ul>Sin código - %s</ul>' % line['nombre_cuenta'] not in acc_error_log:
                            acc_error_log.append('<ul>Sin código - %s</ul>' % line['nombre_cuenta'])
            else:
                return self.refresh('<strong style="color:red">No hay cuentas para el mes seleccionado. </strong>')

        if rut_error_log:
            log.append('<p>Los siguientes RUT no se encuentran asignados a ningún contacto:</p> %s' % ''.join(map(str, rut_error_log)))
        if acc_error_log:
            log.append('<p>Las siguientes cuentas no han sido encontradas: %s' % ''.join(map(str, acc_error_log)))
        if aaa_error_log:
            log.append('<p>Las siguientes cuentas analíticas o distribuciones analíticas no han sido encontradas: %s' % ''.join(map(str, aaa_error_log)))
        if not log:
            self.move_id = move_created
            self.state = 'done'
            self.message = 'Importación exitosa. Se creó el asiento %s' % self.move_id.name
            return {
                'name': self.move_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': self.move_id.id,
            }
        else:
            move_created._cr.rollback()
            self._cr.rollback()
            str_log = '<br/>'.join(map(str, log))
            return self.refresh('<strong style="color:red">La importación ha fallado:</strong> <br>'+str_log)

        return refresh

        # else:
        #     self.write({'moves_found': False})