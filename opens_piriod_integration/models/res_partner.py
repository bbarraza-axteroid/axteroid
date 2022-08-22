from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    piriod_customer_id = fields.Char(string='ID del cliente piriod')

    def create_piriod_customer(self, customer_json):
        if customer_json:
            country = self.env['res.country'].sudo().search([('name', '=', customer_json["country"]["name"])])
            data = {
                'piriod_customer_id': customer_json["id"],
                'name': customer_json["name"],
                'create_date': customer_json["created"],
                'country_id': country.id,
                'l10n_latam_identification_type_id': 4,
                'vat': customer_json["tax_id"],
                'website': customer_json["website"],
                'street': customer_json["address"],
                'email': customer_json["email"],
                'phone': customer_json["phone"],
            }
            odoo_customer = self.env['res.partner'].sudo().create(data)
            odoo_customer.l10n_cl_sii_taxpayer_type = '1'
            return odoo_customer