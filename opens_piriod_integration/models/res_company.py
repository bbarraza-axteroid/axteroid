from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    organization_id = fields.Char(string='ID Organización Piriod')
    token = fields.Char(string='Token Piriod')
    piriod_connection_url = fields.Char(string='URL API Piriod')