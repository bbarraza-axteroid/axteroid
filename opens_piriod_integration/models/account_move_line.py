from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def create_piriod_lines(self, lines_json, company_id):
        if lines_json:
            settings = self.env['ir.config_parameter'].sudo()
            account_id = settings.get_param('piriod_account_id')
            account_id = int(account_id)
            lines = [(5,)]
            for line in lines_json:
                odoo_producto = self.env['product.template'].sudo().search([('name', '=', line["name"])])
                if not odoo_producto:
                    odoo_producto = self.env['product.template'].create_piriod_product(line, company_id)
                lines.append((0, 0, {
                    'tax_ids': odoo_producto.taxes_id.ids,
                    'product_id': odoo_producto.id,
                    'name': line["name"],
                    'price_unit': line["amount"],
                    'quantity': line["quantity"],
                    'account_id': account_id,
                    'price_subtotal': line["total"],
                    'discount':line["discount"]
                }))
            return lines
