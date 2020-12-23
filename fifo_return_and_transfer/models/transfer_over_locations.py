# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class TransferOverLocations(models.Model):
    _name = "transfer.over.locations"

    source_location_id = fields.Many2one("stock.location", string="Source Location",
                                         domain=[("usage", "=", "internal")])
    destination_location_id = fields.Many2one("stock.location", string="Destination Location",
                                              domain=[("usage", "=", "internal")])
    product_ids = fields.One2many(comodel_name="transfer.over.locations.lines", inverse_name="transfer_id",
                                  string="Products")
    state = fields.Selection(string="State", selection=[("draft", "Draft"), ("available", "Available")
                                                        , ("confirmed", "Confirmed"),
                                                        ("transferred", "Transferred")],
                             default="draft")
    reference = fields.Char(string="Reference")
    name = fields.Char("Name", default="/", readonly=True, required=True)
    all_picking_to_be_returned = fields.Text()
    all_move_vals = fields.Text()
    company_id = fields.Many2one('res.company', string='Company', index=True, required=1, default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, vals):
        if vals.get("name", "/"):
            vals["name"] = self.env["ir.sequence"].next_by_code("transfer.over.locations")
        return super(TransferOverLocations, self).create(vals)

    def _check_available_qty(self):
        self.ensure_one()
        for line in self.product_ids:
            rounding = line.product_id.uom_id.rounding

            # check for lots always
            if not line.lot_ids:
                raise ValidationError(
                    _("You need to supply a Lot/Serial number for product {} ".format(line.product_id.name)))

            # Lot tracking
            if line.product_id.tracking == "lot":
                raise ValidationError(_(
                    "You Can not transfer product {}. Only avialable transfer products with Serials or no tracking.\n".format(
                        line.product_id.name)))
            # No tracking
            elif line.product_id.tracking == "none":
                total_available_qty = self.env['stock.quant']._get_available_quantity(line.product_id, self.source_location_id)
                if float_compare(total_available_qty, line.quantity, precision_rounding=rounding) < 0:
                    raise ValidationError(
                        _("There is no available quantity for product {} in the source location.\n"
                          "There is only {} available".format(line.product_id.name, total_available_qty)))
            # Serial tracking
            elif line.product_id.tracking == "serial":
                if not line.lot_ids:
                    raise ValidationError(
                        _("You need to supply a Lot/Serial number for product {} ".format(line.product_id.name)))

                qty_in_line_lots = sum(line.lot_ids.mapped('quantity'))
                if float_compare(qty_in_line_lots, line.quantity, precision_rounding=rounding) != 0:
                    raise ValidationError(_("You need to supply a Lot/Serial number for product {} same as the product quantity".format(
                                line.product_id.name)))
                unavailable_lots = []
                for l in line.lot_ids:
                    lot_id = l.lot_id
                    total_available_qty = self.env['stock.quant']._get_available_quantity(line.product_id, self.source_location_id, lot_id=lot_id)
                    if float_compare(total_available_qty, l.quantity, 5) < 0:
                        unavailable_lots.append(_("Serial [{}] of product [{}] in the source location, available quantity [{}] \n".format(lot_id.name, line.product_id.name, total_available_qty)))
                if unavailable_lots:
                    message = ''
                    for m in unavailable_lots:
                        message += m
                    raise ValidationError(
                        _("There is no available quantity for serials:\n {}".format(message)))

    def check_available_moves(self):
        for record in self:
            # Validation
            if not record.product_ids:
                raise ValidationError(_("There is no products to transfer"))

            in_picking_type_id = record.company_id.internal_receipt_id
            return_picking_type_id = record.company_id.return_picking_type_id
            if not in_picking_type_id or not return_picking_type_id:
                raise ValidationError(_("There is no Picking Types for internal transfer"))

            record._check_available_qty()
            record.state = "available"
        return True

    @api.model
    def _prepare_picking(self, is_return=False):
        return_picking_type_id = self.company_id.return_picking_type_id
        in_picking_type_id = self.company_id.internal_receipt_id
        customer_location_id, vendor_location_id = self.env["stock.warehouse"]._get_partner_locations()
        return {
            'picking_type_id': return_picking_type_id.id if is_return else in_picking_type_id.id,
            'date': fields.Date.today(),
            'origin': self.name,
            'location_dest_id': vendor_location_id.id if is_return else self.destination_location_id.id,
            'location_id': self.source_location_id.id if is_return else vendor_location_id.id,
            'company_id': self.company_id.id,
        }

    def _prepare_stock_moves(self, line, picking):
        self.ensure_one()
        move_lines = self.env['stock.move.line'].sudo().search([("location_dest_id", "=", self.source_location_id.id),
                 ("product_id", "=", line.product_id.id),
                 ("lot_id", "in", line.lot_ids.mapped("lot_id").ids),
                 ("state", "in", ["done"])])

        moves_dict = {}
        lot_line_ids_from_moves = self.env['transfer.over.locations.lines']
        for move_line in move_lines:
            lot_line_ids = line.lot_ids.filtered(lambda x: x.lot_id == move_line.lot_id)
            if lot_line_ids_from_moves:
                lot_line_ids_from_moves += lot_line_ids
            else:
                lot_line_ids_from_moves = lot_line_ids

            quantity = sum(lot_line_ids.mapped('quantity'))
            if move_line.move_id in moves_dict:
                moves_dict[move_line.move_id]['lot_line_ids'] += lot_line_ids
                moves_dict[move_line.move_id]['quantity'] += quantity
                moves_dict[move_line.move_id]['value'] += move_line.move_id.price_unit * quantity
            else:
                moves_dict[move_line.move_id] = {
                    'move_id': move_line.move_id,
                    'price_unit': move_line.move_id.price_unit,
                    'value': move_line.move_id.price_unit * quantity,
                    'lot_line_ids': lot_line_ids,
                    'quantity': quantity
                }

        vals = []
        for key in moves_dict:
            vals.append(
                {
                    'name': self.name,
                    'origin': picking.name or self.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': moves_dict[key]['quantity'],
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'price_unit': moves_dict[key]['price_unit'],
                    'value': moves_dict[key]['value'],
                    'move_line_ids': [(0, 0, {'product_id': line.product_id.id,
                                              'product_uom_id': line.product_id.uom_id.id,
                                              'product_uom_qty': l.quantity,
                                              'qty_done': l.quantity,
                                              'location_id': picking.location_id.id,
                                              'location_dest_id': picking.location_dest_id.id,
                                              'lot_id': l.lot_id.id, }) for l in moves_dict[key]['lot_line_ids']],
                    'picking_id': picking.id
                }
            )

        if lot_line_ids_from_moves:
            remaining_lot_lines_without_moves = line.lot_ids - lot_line_ids_from_moves
        else:
            remaining_lot_lines_without_moves = line.lot_ids

        if remaining_lot_lines_without_moves:
            vals.append(
                {
                    'name': self.name,
                    'origin': picking.name or self.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': sum(remaining_lot_lines_without_moves.mapped('quantity')),
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'price_unit': 0,
                    'value': 0,
                    'move_line_ids': [(0, 0, {'product_id': line.product_id.id,
                                              'product_uom_id': line.product_id.uom_id.id,
                                              'product_uom_qty': l.quantity,
                                              'qty_done': l.quantity,
                                              'location_id': picking.location_id.id,
                                              'location_dest_id': picking.location_dest_id.id,
                                              'lot_id': l.lot_id.id, }) for l in remaining_lot_lines_without_moves],
                    'picking_id': picking.id
                }
            )
        return vals

    def _create_stock_moves(self, picking):
        self.ensure_one()
        values = []
        for line in self.product_ids:
            for v in self._prepare_stock_moves(line, picking):
                values.append(v)
        return self.env['stock.move'].sudo().create(values)

    def create_return_picking(self):
        self.ensure_one()
        StockPicking = self.env['stock.picking'].sudo()
        res = self._prepare_picking(is_return=True)
        picking = StockPicking.create(res)
        moves = self._create_stock_moves(picking)
        moves._action_assign()
        if picking.state == 'draft':
            picking.action_confirm()
        if picking.state != 'assigned':
            picking.action_assign()
        if picking.state != 'done':
            picking.action_done()
        return picking

    @api.multi
    def action_confirm(self):
        for record in self:
            if not record.state == 'available':
                continue
            record.create_return_picking()
            record.state = "confirmed"
        return True

    def create_final_transfer_picking(self):
        self.ensure_one()
        StockPicking = self.env['stock.picking'].sudo()
        res = self._prepare_picking()
        picking = StockPicking.create(res)
        moves = self._create_stock_moves(picking)
        moves._action_assign()
        if picking.state == 'draft':
            picking.action_confirm()
        if picking.state != 'assigned':
            picking.action_assign()
        if picking.state != 'done':
            picking.action_done()
        return picking

    @api.multi
    def do_transfer(self):
        for record in self:
            if not record.state == 'confirmed':
                continue
            picking = record.create_final_transfer_picking()
            record.state = "transferred"
            return {
                "domain": [("id", "=", picking.id)],
                "name": "Picking",
                "view_type": "form",
                "view_mode": "tree,form",
                "res_model": "stock.picking",
                "type": "ir.actions.act_window",
            }