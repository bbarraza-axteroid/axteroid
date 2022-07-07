from odoo import http
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
        if not json:
            return Response(status=400)
        piriod_invoice_id = json.get('object_id')

        # piriod_signature = request.httprequest.headers.get('x-piriod-signature')
        # _logger.info(piriod_signature)
        # if not request.env['account.move'].sudo().signature_is_valid(piriod_signature):
        #     return Response(status=400)

        if json.get('event') == 'invoice.finalized':
            #Resuesta de la factura
            invoice = request.env['account.move'].sudo().get_piriod_invoice(piriod_invoice_id)
            if not invoice.status_code == requests.codes.ok:
                return Response(status=404)
            invoice_json = invoice.json()
            _logger.info(invoice_json)
            #Respuesta del pdf de la factura
            invoice_pdf = request.env['account.move'].sudo().get_piriod_invoice_pdf(piriod_invoice_id)
            if not invoice_pdf.status_code == requests.codes.ok:
                return Response(status=404)
            invoice_pdf_json = invoice_pdf.json()

            #Respuesta del xml de la factura (No esta funcionando con cambiar pdf por xml)
            # invoice_xml = request.env['account.move'].sudo().get_piriod_invoice_xml(piriod_invoice_id)
            # if not invoice_xml.status_code == requests.codes.ok:
            #     return Response(status=404)
            # invoice_xml_json = invoice_xml.json()
            # print(invoice_xml_json)

            request.env['account.move'].sudo().create_piriod_invoice(invoice_json, invoice_pdf_json)
        else:
            return Response(status=400)
        return Response(status=200)