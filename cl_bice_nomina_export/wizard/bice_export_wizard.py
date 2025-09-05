from odoo import models, fields
import base64
from io import StringIO

class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportador BICE para nómina de proveedores'

    batch_payment_id = fields.Many2one('account.batch.payment', string="Pago por Lote")
    file_data = fields.Binary('Archivo BICE')
    file_name = fields.Char('Nombre Archivo')

    def generate_csv_bice(self):
        lines = []
        for payment in self.batch_payment_id.payment_ids:
            partner = payment.partner_id

            # Generar campos con formato fijo (ajustar de acuerdo al PDF)
            rut = (partner.vat or '').replace('-', '').replace('.', '').ljust(10)[:10]
            nombre = (partner.name or '').ljust(40)[:40]
            banco = (partner.bank_ids[:1].bank_id.code or '').ljust(3)[:3] if partner.bank_ids else '000'
            cuenta = (partner.bank_ids[:1].acc_number or '').zfill(20)[:20] if partner.bank_ids else '00000000000000000000'
            monto = str(int(payment.amount * 100)).zfill(10)
            email = (partner.email or '').ljust(50)[:50]

            linea = f'{rut}{nombre}{banco}{cuenta}{monto}{email}'
            lines.append(linea)

        output = '\r\n'.join(lines)

        self.file_data = base64.b64encode(output.encode('utf-8'))
        self.file_name = f'nomina_bice_proveedores.csv'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bice.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
