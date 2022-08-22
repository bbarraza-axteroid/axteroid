import base64

from odoo import fields, models
import requests
import logging
import hashlib
import hmac

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    piriod_id = fields.Char(string='ID de la factura piriod')

    def get_piriod_invoice(self, piriod_invoice_id):
        companys = self.env['res.company'].sudo().search([])

        for company in companys:
            api, token, organization = company.get_piriod_data()
            headers = {
                'Authorization': 'Token %s' % (token),
                'x-simple-workspace': organization
            }

            r = requests.get('%s/invoices/%s/' %
                             (api, piriod_invoice_id), headers=headers)

            if r and r.status_code == 200:
                invoice_json = r.json()
                log = {
                    'name': "Datos factura",
                    'url_used': '%s/invoices/%s/' % (api, piriod_invoice_id),
                    'JSON_entrada': invoice_json
                }
                self.env['piriod.webhook.log'].sudo().create(log)

                return r, company.id
        return False, False

    def create_piriod_invoice(self, invoice_json, company_id):
        if invoice_json:
            Partner = self.env['res.partner']
            Document = self.env['l10n_latam.document.type']
            Log = self.env['piriod.webhook.log']

            odoo_partner = Partner.search(
                [('name', '=', invoice_json["customer"]["name"])])
            if not odoo_partner:
                odoo_partner = Partner.create_piriod_customer(
                    invoice_json["customer"])

            odoo_document = Document.search(
                [('code', '=', invoice_json["document"]["code"])])
            if not odoo_document:
                odoo_document = Document.create_piriod_document(
                    invoice_json["document"])

            journal = self.env['account.journal'].sudo().search(
                [('code', '=', 'INV'), ('company_id', '=', int(company_id))])
            if not journal:
                return 100

            lines = self.create_piriod_lines(
                    invoice_json["lines"], company_id)

            data = {
                'company_id': int(company_id),
                'move_type': 'out_invoice',
                'piriod_id': invoice_json["id"],
                'partner_id': odoo_partner.id,
                'invoice_date': invoice_json["date"],
                'invoice_date_due': invoice_json["due_date"],
                'currency_id': 45,
                'l10n_latam_document_type_id': odoo_document.id,
                'journal_id': journal.id,
                'invoice_line_ids': lines
            }

            try:
                odoo_invoice = self.env['account.move'].sudo().create(data)
            except Exception as e:
                _logger.info(e)
                #Log.sudo().create({
                #    'name': "ERROR",
                #    #'url_used': '%s/invoices/%s/' % (api, piriod_invoice_id),
                #    'error': 'Falló la creación de Factura. Revisar Log',
                #    'invoice_id': invoice_json["id"]
                #})
                return 200

            folio_piriod_ext = invoice_json['number']
            new_name = odoo_invoice.sequence_prefix + \
                str(folio_piriod_ext).zfill(6)
            odoo_invoice.write(
                {'name': new_name, 'payment_reference': new_name, 'sequence_number': folio_piriod_ext})

            if odoo_invoice:
                # obtener pdf/xml
                invoice_json_id = invoice_json["id"]
                pdf_result = self.get_piriod_invoice_pdf(invoice_json_id, company_id)

                if pdf_result:
                    pdf_b64 = pdf_result.json()['file']
                    attachment_name_pdf = str(folio_piriod_ext) + ".pdf"
                    attachment_name_xml = str(folio_piriod_ext) + ".xml"
                    self.env['ir.attachment'].sudo().create({
                        'type': 'binary',
                        'name': attachment_name_pdf,
                        'res_model': 'account.move',
                        'datas': pdf_b64,
                        'res_id': odoo_invoice.id,
                    })

                    xml_b64 = self.get_piriod_invoice_xml(invoice_json, company_id)

                    if xml_b64:
                        self.env['ir.attachment'].sudo().create({
                            'type': 'binary',
                            'name': attachment_name_xml,
                            'res_model': 'account.move',
                            'datas': xml_b64,
                            'res_id': odoo_invoice.id,
                        })

        return odoo_invoice

    def create_piriod_lines(self, lines_json, company_id):
        if lines_json:
            account_id = self.env.company.piriod_account_id.id
            lines = [(5,)]
            Product = self.env['product.template']

            for line in lines_json:
                odoo_producto = Product.sudo().search([('name', '=', line["name"]),
                                                       ('company_id', '=', company_id)])
                if not odoo_producto:
                    odoo_producto = Product.create_piriod_product(
                        line, company_id)

                lines.append((0, 0, {
                    'tax_ids': odoo_producto.taxes_id.ids,
                    'product_id': odoo_producto.id,
                    'name': line["name"],
                    'price_unit': line["amount"],
                    'quantity': line["quantity"],
                    'account_id': int(account_id),
                    'price_subtotal': line["total"],
                    'discount':line["discount"]
                }))

            return lines

    def get_piriod_invoice_pdf(self, piriod_invoice_id, company_id):
        company = self.env['res.company'].sudo().search([('id', '=', company_id)])
        try:
            api, token, organization = company.get_piriod_data()
            credentials = {
                'Authorization': f'Token {token}',
                'x-simple-workspace': f'{organization}'
            }
            r = requests.get(f'{api}/invoices/{piriod_invoice_id}/pdf/', headers=credentials)
            if r:
                pdf_json = r.json()
                log = {
                    'name': "Datos pdf",
                    'url_used': f'{api}/invoices/{piriod_invoice_id}/pdf/',
                    'JSON_entrada': pdf_json
                }
                self.env['piriod.webhook.log'].sudo().create(log)
            return r
        except:
            return False

    def get_piriod_invoice_xml(self, invoice_json, company_id):
        try:
            company = self.env['res.company'].sudo().search([('id', '=', company_id)])
            api, token, organization = company.get_piriod_data()
            credentials = {
                'Authorization': f'Token {token}',
                'x-simple-workspace': f'{organization}'
            }
            return base64.b64encode(requests.get(invoice_json['local_file']).content)
        except:
            return False

    def signature_is_valid(self, piriod_signature):
        WH_SECRET = 'whsecret_q48kQSw4m3t5MvzOuJpk6MeLv6i3FLX2WFDsJBpRLWrIWgsLpEDoz43'
        if not WH_SECRET == piriod_signature:
            return False
        return True