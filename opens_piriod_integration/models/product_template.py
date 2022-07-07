from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def create_piriod_product(self, product):
        if product:
            data = {
                'name': product["name"]
            }
            odoo_product = self.env['product.template'].create(data)
            return odoo_product