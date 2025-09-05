# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import csv
from datetime import date

class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    filename = fields.Char(string="Nombre", default="proveedores.csv", required=True)

    def action_generate(self):
        """Genera el CSV (sin encabezados) y lo adjunta al lote."""
        self.ensure_one()
        # Contexto: debe venir desde un lote (account.batch.payment)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        if active_model != "account.batch.payment" or not active_id:
            raise UserError(_("Este asistente debe abrirse desde un Lote de Pagos."))

        batch = self.env["account.batch.payment"].browse(active_id)
        if not batch or len(batch) != 1:
            raise UserError(_("No se encontró el Lote de Pagos."))

        # Construimos el CSV en memoria (sin encabezados)
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, delimiter=",", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)

        # === GENERA UNA FILA POR PAGO ===
        for payment in batch.payment_ids.filtered(lambda p: p.state in ("sent", "posted", "reconciled", "draft", "approved")):
            row = self._bice_row(batch, payment)
            if row:
                writer.writerow(row)

        data = buf.getvalue().encode("utf-8")
        buf.close()

        # Borro adjuntos previos que empiecen con 'proveedores'
        old = self.env["ir.attachment"].search([
            ("res_model", "=", "account.batch.payment"),
            ("res_id", "=", batch.id),
            ("name", "ilike", "proveedores")
        ])
        if old:
            old.unlink()

        # Creo adjunto
        fname = self.filename or "proveedores.csv"
        attachment = self.env["ir.attachment"].create({
            "name": fname,
            "res_model": "account.batch.payment",
            "res_id": batch.id,
            "type": "binary",
            "datas": base64.b64encode(data),
            "mimetype": "text/csv",
        })

        # Mensaje en el chatter con link al adjunto
        batch.message_post(
            body=_("Archivo BICE generado: <b>%s</b> (adjunto)") % fname,
            attachment_ids=[attachment.id],
        )

        # Cierro el wizard y refresco la vista
        return {"type": "ir.actions.act_window_close"}

    # -------------------------------------------------------------------------
    # MAPEADOR: Ajusta el orden de columnas aquí (sin headers)
    # -------------------------------------------------------------------------
    def _bice_row(self, batch, payment):
        """
        Devuelve la fila (list) en el orden requerido por BICE Proveedores.
        Este layout es el más usado; si tu PDF indica otro, sólo reordena.

        Orden propuesto (11 columnas, sin encabezados):
          1  Rut beneficiario                     -> partner.vat (formato 99999999-K, sin puntos)
          2  Dígito verificador                   -> extraído del RUT (K en mayúscula)
          3  Nombre beneficiario                  -> partner.name
          4  Tipo cuenta destino (Texto/Cód.)     -> mapea desde partner.bank_id.acc_type
          5  Nº cuenta destino                    -> partner.bank_id.acc_number
          6  Código banco destino (BICE code)     -> mapea desde bank.bic o bank.code (ver _bank_code)
          7  Monto (enteros, sin separadores)     -> en CLP, sin decimales (redondeo normal)
          8  Email aviso                          -> partner.email (o vacío)
          9  Glosa/Referencia                     -> payment.ref o batch.name
         10  Fecha de ejecución (YYYYMMDD)        -> batch.date (o hoy)
         11  Moneda                               -> 'CLP'
        """
        partner = payment.partner_id
        if not partner:
            raise ValidationError(_("El pago %s no tiene proveedor.") % (payment.name or payment.id))

        # RUT y DV (limpio: sin puntos, en mayúscula)
        rut_raw = (partner.vat or "").replace(".", "").replace(" ", "").upper()
        rut_num, dv = self._split_rut(rut_raw)

        # Banco/cuenta destino
        bankacc = partner.bank_ids[:1]  # primera cuenta bancaria del partner
        acc_type = self._map_account_type(bankacc.acc_type if bankacc else "")
        acc_number = (bankacc.acc_number or "") if bankacc else ""
        bank_code = self._bank_code(bankacc.bank_id) if bankacc and bankacc.bank_id else ""

        # Monto en CLP como entero (sin separadores ni decimales)
        # Si tu monto viene en otra moneda, aquí puedes convertirlo a CLP antes.
        amount = round(payment.amount or 0)

        # Email aviso y referencia
        email = partner.email or ""
        ref = payment.ref or batch.name or ""

        # Fecha de ejecución
        exec_date = (batch.date or date.today()).strftime("%Y%m%d")

        # Moneda
        currency = "CLP"

        row = [
            rut_num,            # 1
            dv,                 # 2
            partner.name or "", # 3
            acc_type,           # 4
            acc_number,         # 5
            bank_code,          # 6
            str(amount),        # 7
            email,              # 8
            ref,                # 9
            exec_date,          # 10
            currency,           # 11
        ]
        return row

    # ----------------- Helpers -----------------
    def _split_rut(self, rut):
        """
        Recibe '76104754-K' o '76104754K' y retorna ('76104754','K').
        Si no hay DV, retorna ('','').
        """
        if not rut:
            return "", ""
        rut = rut.replace("-", "")
        if len(rut) < 2:
            return rut, ""
        return rut[:-1], rut[-1]

    def _map_account_type(self, acc_type):
        """
        Mapea tipos de cuenta de Odoo a los valores que exige BICE.
        Ajusta los códigos/textos según tu PDF.
        """
        t = (acc_type or "").lower()
        # Ejemplos: 'current' (corriente), 'savings' (vista/ahorro), 'rut' (cuentaRUT), etc.
        if t in ("current", "corriente", "checking"):
            return "CTA_CTE"     # cámbialo por el código que pida BICE
        if t in ("savings", "vista", "ahorro"):
            return "CTA_VISTA"   # cámbialo por el código que pida BICE
        if t in ("rut", "cuentarut"):
            return "RUT"
        return "CTA_CTE"         # por defecto

    def _bank_code(self, bank):
        """
        Retorna el código de banco exigido por BICE.
        Intenta bank.bic, bank.code o nombre.
        Ajusta el mapeo puntual aquí si BICE pide códigos específicos.
        """
        if not bank:
            return ""
        # Primero usa un código si viene definido
        if getattr(bank, "code", False):
            return bank.code
        if getattr(bank, "bic", False):
            return bank.bic

        name = (bank.name or "").strip().lower()
        # Mínimo mapeo local. Ajusta con los códigos de tu PDF.
        # Ejemplos (completa con los tuyos):
        if "bice" in name:
            return "028"  # ejemplo
        if "estado" in name:
            return "012"
        if "chile" in name:
            return "009"
        if "santander" in name:
            return "037"
        if "scotiabank" in name:
            return "014"
        if "itau" in name or "itaú" in name:
            return "039"
        return ""
