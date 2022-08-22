from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    organization_id = fields.Char(string='ID Organización Piriod')
    token = fields.Char(string='Token Piriod')
    piriod_connection_url = fields.Char(string='URL API Piriod')
    piriod_account_id = fields.Many2one('account.account', string="Cuenta de Piriod")

    def get_piriod_data(self):
        api = self.piriod_connection_url
        token = self.token
        organization = self.organization_id

        return api, token, organization