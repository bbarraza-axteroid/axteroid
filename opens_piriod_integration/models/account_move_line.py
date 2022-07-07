from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    piriod_id = fields.Char(string='ID de la factura piriod')

    def create_piriod_lines(self, lines_json):
        if lines_json:
            lines = [(5,)]
            tax_ids = [(1,)]
            for line in lines_json:
                odoo_producto = self.env['product.template'].sudo().search([('name', '=', line["name"])])
                if not odoo_producto:
                    odoo_producto = self.env['product.template'].create_piriod_product(line)
                print(line)
                lines.append((0, 0, {
                    'tax_ids': odoo_producto.taxes_id.ids,
                    'product_id': odoo_producto.id,
                    'name': line["name"],
                    'price_unit': line["amount"],
                    'quantity': line["quantity"],
                    'account_id': 132,
                    'price_subtotal': line["total"],
                    'discount':line["discount"]
                }))
            return lines
