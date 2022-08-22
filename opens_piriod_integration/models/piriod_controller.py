from odoo import http, models, fields
from odoo.http import Response
from odoo.http import request
import logging
import requests
import base64

_logger = logging.getLogger(__name__)

# Controlador para exponer recursos a piriod


class PiriodController(http.Controller):

    # Expone el recurso al que se conecta piriod para informar la creacion de un invoice
    @http.route('/api/piriod_webhook_invoice', type="json", auth='public', methods=['POST'], csrf=False)
    def piriod_webhook_invoice(self, **kw):
        AccountMove = request.env['account.move']
        Log = request.env['piriod.webhook.log']
        Company = request.env['res.company']

        json = request.jsonrequest
        request.env['piriod.webhook.log'].sudo().create({
            'name': "Activacion de evento",
            'JSON_entrada': json
        })

        if not json:
            return Response(status=400)

        piriod_invoice_id = json.get('object_id')

        if json.get('event') == 'invoice.finalized':
            _logger.info('PROCESSING INVOICE')
            resp, company_id = AccountMove.get_piriod_invoice(piriod_invoice_id)
            company = Company.search([('id', '=', company_id)])
            api, token, organization = company.get_piriod_data()

            if not resp:
                Log.sudo().create({
                    'name': "ERROR",
                    'url_used': '%s/invoices/%s/' % (api, piriod_invoice_id),
                    'error': 'No se encontró factura en la URL especificada.',
                    'invoice_id': None
                })

                return Response(status=404)

            elif resp and resp.status_code != 200:
                Log.sudo().create({
                    'name': "ERROR",
                    'url_used': '%s/invoices/%s/' % (api, piriod_invoice_id),
                    'error': 'Problema en la autenticación',
                    'invoice_id': None
                })

                return Response(status=resp.status_code)

            invoice_json = resp.json()
            is_duplicate = request.env['account.move'].sudo().search(
                [('piriod_id', '=', invoice_json["id"]), ('company_id', '=', company_id)])

            if is_duplicate:
                _logger.info('DUPLICATED INVOICE')
                log = {
                    'name': "Factura Duplicada",
                    'JSON_entrada': invoice_json
                }
                Log.sudo().create(log)
            else:
                invoice = AccountMove.create_piriod_invoice(invoice_json, company_id)
                if invoice == 100:
                    msg = 'No existe diario para Facturas'
                    _logger.info(msg)
                    Log.sudo().create({
                        'name': "ERROR",
                        'url_used': '%s/invoices/%s/' % (api, piriod_invoice_id),
                        'error': msg,
                        'invoice_id': invoice_json["id"]
                    })
                    return Response(msg, status=404)
                elif invoice == 200:
                    msg = 'Falló la creación de Factura. Revisar Log'
                    _logger.info(msg)
                    return Response(msg, status=400)
                return Response(status=200)
        else:
            return Response(status=400)
        
        #return Response(status=200)


class PiriodWebhookLog(models.Model):
    _name = 'piriod.webhook.log'

    name = fields.Char(string='Nombre')
    url_used = fields.Char(string="url utilizada en request")
    JSON_entrada = fields.Char(string="Json obtenido")

    error = fields.Char(string="Mensaje de error")
    invoice_id = fields.Char(string="Factura relacionada")
