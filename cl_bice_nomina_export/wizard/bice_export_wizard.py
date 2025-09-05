from odoo import models, fields
import base64
import csv
from io import StringIO


class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportar archivo Proveedores Banco BICE'

    batch_id = fields.Many2one(
        'account.batch.payment',
        string='Batch',
        required=True,
        readonly=True,
    )

    def action_generate(self):
        """Genera el CSV, lo adjunta al lote y vuelve al lote."""
        self.ensure_one()

        # --- Generar CSV en memoria ---
        buf = StringIO(newline='')
        writer = csv.writer(buf, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Cabecera de ejemplo (ajústala a tu layout real)
        writer.writerow(['Rut', 'Nombre', 'Cuenta', 'Monto'])

        # Detalle desde los pagos del lote
        for payment in self.batch_id.payment_ids:
            partner = payment.partner_id
            writer.writerow([
                (partner.vat or '').strip(),
                (partner.name or '').strip(),
                (payment.partner_bank_id.acc_number or '').strip(),
                f"{payment.amount:.2f}",
            ])

        csv_content = buf.getvalue()
        buf.close()

        # --- Crear attachment ---
        attachment = self.env['ir.attachment'].create({
            'name': 'proveedores_bice.csv',
            'type': 'binary',
            'datas': base64.b64encode(csv_content.encode('utf-8')),
            'mimetype': 'text/csv',
            'res_model': 'account.batch.payment',
            'res_id': self.batch_id.id,
        })

        # Mensaje en el chatter
        self.batch_id.message_post(
            body="Archivo BICE Proveedores generado y adjuntado.",
            attachment_ids=[attachment.id],
        )

        # Volver al lote
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.batch.payment',
            'view_mode': 'form',
            'res_id': self.batch_id.id,
        }
