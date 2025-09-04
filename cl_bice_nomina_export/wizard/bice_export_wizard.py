import base64
import csv
import io
import re
import unicodedata
from odoo import fields, models, _
from odoo.exceptions import UserError

RUT_CLEAN_RE = re.compile(r"[^0-9Kk]")
ONLY_DIGITS_RE = re.compile(r"\D")
MAIL_OK_RE = re.compile(r"^[A-Za-z0-9._\-]+@[A-Za-z0-9._\-]+\.[A-Za-z]{2,}$")

class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    batch_id = fields.Many2one("account.batch.payment", required=True, readonly=True)
    journal_id = fields.Many2one("account.journal", domain=[("type", "=", "bank")], required=True)
    execution_date = fields.Date(string="Fecha de ejecución", default=fields.Date.context_today, required=True)

    include_header = fields.Boolean(string="Incluir cabecera CSV", default=False)
    encoding = fields.Selection([
        ("utf-8-sig", "UTF-8"),
        ("latin1", "Latin-1 / ISO-8859-1"),
    ], string="Codificación", default="utf-8-sig")

    factura_default = fields.Char(
        string="Factura por defecto",
        help="Si algún pago no tiene referencia, se usará este valor (máx 15, sin espacios)."
    )
    include_email = fields.Boolean(string="Incluir Email del beneficiario", default=True)

    file_data = fields.Binary(string="Archivo", readonly=True)
    file_name = fields.Char(string="Nombre", readonly=True)

    layout_help = fields.Html(compute="_compute_layout_help")

    def _compute_layout_help(self):
        for wiz in self:
            wiz.layout_help = _(
                """
                <p>Layout BICE Proveedores (CSV delimitado por coma):</p>
                <ol>
                  <li>Nombre Titular</li>
                  <li>RUT Titular (sin puntos ni guion, con DV)</li>
                  <li>Cuenta Titular</li>
                  <li>Monto</li>
                  <li>Banco (código CCA)</li>
                  <li>Tipo de Cuenta (1=Vista, 2=Ahorro, 3=Corriente/RUT)</li>
                  <li>Moneda (0)</li>
                  <li>Oficina Origen (1)</li>
                  <li>Oficina Destino (1)</li>
                  <li>Factura</li>
                  <li>Mail Beneficiario (opcional)</li>
                </ol>
                <p><i>Fuente: Manual BICE 2024 - Pago en Línea (Proveedores).</i></p>
                """
            )

    @staticmethod
    def _strip_accents(text: str) -> str:
        if not text:
            return ""
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    @staticmethod
    def _clean_name(name: str) -> str:
        s = (name or "").strip()
        s = BiceExportWizard._strip_accents(s).replace("Ñ", "N").replace("ñ", "n")
        s = re.sub(r"[.\-]", " ", s)
        s = re.sub(r"\s+", " ", s)
        return s[:40]

    @staticmethod
    def _clean_rut(vat: str) -> str:
        s = (vat or "").upper()
        s = s.replace(".", "").replace("-", "")
        s = RUT_CLEAN_RE.sub("", s)
        return s[:11]

    @staticmethod
    def _clean_acc_number(num: str) -> str:
        return ONLY_DIGITS_RE.sub("", num or "")[:17]

    @staticmethod
    def _map_account_type(code: str) -> str:
        # Tipo de cuenta fijo: Corriente/RUT = "3" (pedido del usuario para pruebas)
        return "3"

    @staticmethod
    def _clean_factura(txt: str) -> str:
        s = (txt or "").strip()
        s = BiceExportWizard._strip_accents(s).replace(" ", "")
        s = re.sub(r"[^A-Za-z0-9._-]", "", s)
        return s[:15]

    @staticmethod
    def _clean_email(mail: str) -> str:
        if not mail:
            return ""
        s = mail.strip().replace("Ñ", "N").replace("ñ", "n")
        return s if MAIL_OK_RE.match(s) else ""

    def _row_from_payment(self, pay, idx):
        partner = pay.partner_id
        pb = pay.partner_bank_id
        if not pb:
            raise UserError(_(f"Pago {pay.name}: falta cuenta bancaria del proveedor."))
        if not partner.vat:
            raise UserError(_(f"{partner.display_name}: falta RUT (VAT)."))

        name = self._clean_name(partner.name)
        rut = self._clean_rut(partner.vat)
        if not rut:
            raise UserError(_(f"{partner.display_name}: RUT inválido."))

        acc_number = self._clean_acc_number(pb.acc_number)
        if not acc_number:
            raise UserError(_(f"{partner.display_name}: número de cuenta inválido."))

        bank = pb.bank_id
        bank_code = (bank.l10n_cl_sbif_code or bank.bic or "").strip()
        if not bank_code:
            raise UserError(_(f"{partner.display_name}: Banco sin código CCA/CMF (configura en el banco)."))

        acc_type = self._map_account_type(getattr(pb, "l10n_cl_account_type", None))

        amount = int(round(pay.amount))
        if amount <= 0:
            raise UserError(_(f"{partner.display_name}: el monto debe ser positivo."))

        factura_raw = pay.ref or pay.communication or pay.move_id.ref or self.factura_default
        factura = self._clean_factura(factura_raw)
        if not factura:
            raise UserError(_(f"Fila {idx}: 'Factura' es obligatorio (completa 'Referencia' del pago o 'Factura por defecto')."))

        email = self._clean_email(partner.email) if self.include_email else ""

        moneda = "0"
        ofi_origen = "1"
        ofi_destino = "1"

        row = [name, rut, acc_number, str(amount), bank_code, acc_type, moneda, ofi_origen, ofi_destino, factura]
        if self.include_email:
            row.append(email)
        return row

    def action_generate(self):
        self.ensure_one()
        if self.batch_id.payment_type != "outbound":
            raise UserError(_(f"Esta nómina aplica a pagos a proveedores (salidas)."))
        payments = self.batch_id.payment_ids
        if not payments:
            raise UserError(_("El lote no contiene pagos."))

        buf = io.StringIO(newline="")
        writer = csv.writer(buf, delimiter=",")
        if self.include_header:
            header = [
                "Nombre Titular","Rut Titular","Cuenta Titular","Monto","Banco",
                "Tipo de Cuenta","Moneda","Oficina Origen","Oficina Destino","Factura"
            ]
            if self.include_email:
                header.append("Mail Beneficiario")
            writer.writerow(header)

        for i, p in enumerate(payments, start=1):
            writer.writerow(self._row_from_payment(p, i))

        content = buf.getvalue()
        raw = content.encode(self.encoding, errors="ignore")
        b64 = base64.b64encode(raw)
        fname = f"bice_proveedores_{fields.Date.to_string(self.execution_date)}.csv"
        self.write({"file_data": b64, "file_name": fname})
        return {
            "type": "ir.actions.act_url",
            "url": f"web/content/?model=bice.export.wizard&id={self.id}&field=file_data&download=true&filename={fname}",
            "target": "self",
        }
