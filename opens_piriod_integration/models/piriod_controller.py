from odoo import http, models, fields
from odoo.http import Response
from odoo.http import request
import logging
import requests
_logger = logging.getLogger(__name__)

#Controlador para exponer recursos a piriod
class PiriodController(http.Controller):

    #Expone el recurso al que se conecta piriod para informar la creacion de un invoice
    @http.route('/api/piriod_webhook_invoice', type="json", auth='public', methods=['POST'], csrf=False)
    def piriod_webhook_invoice(self, **kw):
        _logger.info('###### WEBHOOK INVOICE')
        json = request.jsonrequest
        log = {
            'name': "Activacion de evento",
            'JSON_entrada': json
        }
        request.env['piriod.webhook.log'].sudo().create(log)
        if not json:
            return Response(status=400)
        piriod_invoice_id = json.get('object_id')
        # piriod_signature = request.httprequest.headers.get('x-piriod-signature')
        # piriod_headers = request.httprequest.headers
        # _logger.info('====================================== x-piriod-signature ======================================')
        # _logger.info(piriod_signature)
        # _logger.info(piriod_headers)
        # if not request.env['account.move'].sudo().signature_is_valid(piriod_signature):
        #     return Response(status=400)

        if json.get('event') == 'invoice.finalized':
            #Resuesta de la factura
            invoice, company_id = request.env['account.move'].sudo().get_piriod_invoice(piriod_invoice_id)
            if not invoice.status_code == requests.codes.ok:
                return Response(status=404)
            invoice_json = invoice.json()
            is_duplicate = request.env['account.move'].sudo().search(
                [('piriod_id', '=', invoice_json["id"]), ('company_id', '=', company_id)])
            if is_duplicate:
                log = {
                    'name': "Factura Duplicada",
                    'JSON_entrada': invoice_json
                }
                request.env['piriod.webhook.log'].sudo().create(log)
            else:
                request.env['account.move'].sudo().create_piriod_invoice(invoice_json, company_id)
        else:
            return Response(status=400)
        return Response(status=200)

class PiriodWebhookLog(models.Model):
    _name = 'piriod.webhook.log'

    name = fields.Char(string='Nombre')
    url_used = fields.Char(string="url utilizada en request")
    JSON_entrada = fields.Char(string="Json obtenido")