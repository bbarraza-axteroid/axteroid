from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def create_piriod_product(self, product, company_id):
        if product:
            data = {
                'name': product["name"],
                'company_id':int(company_id)
            }
            odoo_product = self.env['product.template'].sudo().create(data)
            return odoo_product