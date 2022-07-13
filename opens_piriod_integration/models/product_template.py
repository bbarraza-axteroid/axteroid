from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def create_piriod_product(self, product):
        companys = self.env['res.company'].sudo().search([('name', '=', 'AXTEROID')])
        company_id = 3
        for d in companys:
            company_id = d.id
        if product:
            data = {
                'name': product["name"],
                'company_id':int(company_id)

            }
            odoo_product = self.env['product.template'].with_company(int(company_id)).create(data)
            return odoo_product