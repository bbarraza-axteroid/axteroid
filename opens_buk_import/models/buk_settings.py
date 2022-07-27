from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ast import literal_eval


class BukSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    buk_journal_id = fields.Many2one('account.journal', string='Diario para centralización de BUK')
    buk_create_partner = fields.Boolean(
        string='Creación de contactos',
        required=False)

    def get_values(self):
        res = super(BukSettings, self).get_values()
        settings = self.env['ir.config_parameter'].sudo()

        buk_journal_id = settings.get_param('buk.buk_journal_id')
        buk_create_partner = settings.get_param('buk.buk_create_partner')

        res.update(
            buk_journal_id=literal_eval(buk_journal_id) if buk_journal_id else None,
            buk_create_partner=literal_eval(buk_create_partner) if buk_create_partner else None,
        )
        return res


    def set_values(self):
        super(BukSettings, self).set_values()
        workflow = self.env['ir.config_parameter'].sudo()

        workflow.set_param('buk.buk_journal_id', self.buk_journal_id.id)
        workflow.set_param('buk.buk_create_partner', self.buk_create_partner)