# -*- coding: utf-8 -*-
import os
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class TransferOverLocationsLines(models.Model):
    _name = 'transfer.over.locations.lines'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    quantity = fields.Float(default=1.0)
    transfer_id = fields.Many2one(comodel_name="transfer.over.locations", required=True, ondelete='cascade')

    lot_ids = fields.One2many(comodel_name="transfer.over.locations.lot.lines", inverse_name="line_id",
                              string="Lots/Serials")
    file_import = fields.Binary("Import 'csv' File",
                                help="*Import a list of lot/serial numbers from a csv file \n *Only csv files is allowed"
                                     "\n *The csv file must contain a row header namely 'Serial Number'")
    file_name = fields.Char("file name")

    #     importing "csv" file and appending the datas from file to transfer lines
    @api.multi
    def input_file(self):
        if self.file_import:
            file_value = self.file_import.decode("utf-8")
            filename, FileExtension = os.path.splitext(self.file_name)
            if FileExtension != '.csv':
                raise UserError("Invalid File! Please import the 'csv' file")
            data_list = []
            input_file = base64.b64decode(file_value)
            lst = []
            for loop in input_file.decode("utf-8").split("\n"):
                lst.append(loop)
            if 'Serial Number' not in lst[0]:
                raise UserError('Row header name "Serial Number" is not found in CSV file')
            lst_index = lst[0].replace('\r', '').split(',').index("Serial Number")
            lst.pop(0)
            for vals in lst:
                lst_r = []
                for value in vals.split(','):
                    lst_r.append(value)
                if vals and lst_r:
                    data = self.env['stock.production.lot'].search(
                        [('product_id', '=', self.product_id.id), ('name', '=', lst_r[lst_index].replace('\r', ''))])
                    # conditions based on unique serial number
                    if not data:
                        raise UserError(
                            _('Serial Number %s does not belong to product - "%s".') % (
                            str(vals), self.product_id.name))

                    data_list.append((0, 0, {'lot_id': data.id,
                                             'quantity': 1,
                                             'line_id': self.id,
                                             'product_id': self.product_id.id,
                                             }))

            if self.lot_ids:
                self.lot_ids.unlink()

            self.lot_ids = data_list

        else:
            raise UserError("Invalid File! Please import the 'csv' file")
        # view reference for lot_ids
        return {
            'name': _('Serials/Lots'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'transfer.over.locations.lines',
            'views': [(self.env.ref('fifo_return_and_transfer.transfer_over_locations_lines_form').id, 'form')],
            'target': 'new',
            'res_id': self.id,
        }

    def action_show_lots(self):
        return {
            'name': _('Serials/Lots'),
            'type': 'ir.actions.act_window',
            'view_type': 'tree',
            'view_mode': 'tree, form',
            'views': [(self.env.ref('fifo_return_and_transfer.transfer_over_locations_lines_form').id, 'form')],
            'res_model': 'transfer.over.locations.lines',
            'target': 'new',
            'res_id': self.id,

        }


class TransferOverLocationsLotLines(models.Model):
    _name = 'transfer.over.locations.lot.lines'

    lot_id = fields.Many2one(comodel_name="stock.production.lot", string="Lot/Serial", required=True)
    line_id = fields.Many2one(comodel_name="transfer.over.locations.lines", required=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name="product.product", related="line_id.product_id", readonly=True)
    quantity = fields.Float(default=1.0)
