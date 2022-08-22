from odoo import models

class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    def create_piriod_document(self, document_json):
        if document_json:
            data = {
                'country_id': 46,
                'name': document_json["name"],
                'code': document_json["code"]
            }
            odoo_document = self.env['l10n_latam.document.type'].sudo().create(data)
            return odoo_document