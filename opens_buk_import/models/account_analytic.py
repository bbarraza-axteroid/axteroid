# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BukIntegrationWizard(models.Model):
    _inherit = 'account.analytic.account'

    buk_code = fields.Char("Código BUK")



class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    buk_code = fields.Char("Código BUK")