# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TransferOverLocations(models.Model):
    _name = 'transfer.over.locations'

    source_location_id = fields.Many2one('stock.location', string="Source Location",
                                         domain=[('usage', '=', 'internal')])
    destination_location_id = fields.Many2one('stock.location', string="Destination Location",
                                              domain=[('usage', '=', 'internal')])
    product_ids = fields.One2many(comodel_name="transfer.over.locations.lines", inverse_name="transfer_id",
                                  string="Products")
    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('transferred', 'Transferred')],
                             default='draft')
    reference = fields.Char(string="Reference")
    name = fields.Char('Name', default='/', readonly=True, required=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/'):
            vals['name'] = self.env['ir.sequence'].next_by_code('transfer.over.locations')

        return super(TransferOverLocations, self).create(vals)

    def get_product_available_moves(self, product):
        """
            Return All Available moves for each product To be Returned
        """

        available_moves_to_be_returned = []
        # Lot tracking
        if product.product_id.tracking == 'lot':
            raise ValidationError(_(
                "You Can not transfer product {}. Only avialable transfer products with Serials or no tracking.\n".format(
                    product.product_id.name)))
        # No tracking
        elif product.product_id.tracking == 'none':

            available_moves = self.env['stock.move'].search([('location_dest_id', '=', self.source_location_id.id),
                                                             ('product_id', '=', product.product_id.id),
                                                             ('remaining_qty', '>', 0.0),
                                                             ('picking_id', '!=', False),
                                                             ('state', 'in', ['done'])])
            available_quantity = sum(available_moves.mapped('remaining_qty') or [0.0])
            if available_quantity < product.quantity:
                raise ValidationError(
                    _("There is no available quantity for product {} in the source location.\n"
                      "There is only {} available".format(product.product_id.name, available_quantity)))
            for available_move in set(available_moves):
                available_moves_to_be_returned.append({'move': available_move, 'move_lines': []})
        # Serial tracking
        elif product.product_id.tracking == 'serial':
            if not product.lot_ids:
                raise ValidationError(
                    _("You need to supply a Lot/Serial number for product {} ".format(product.product_id.name)))

            if product.lot_ids:
                sum_lines_quantity = sum([line.quantity for line in product.lot_ids])
                if sum_lines_quantity != product.quantity:
                    raise ValidationError(
                        _(
                            "You need to supply a Lot/Serial number for product {} same as the product quantity".format(
                                product.product_id.name)))

            # for lot in product.lot_ids:
            available_move_lines = self.env['stock.move.line'].search(
                [('location_dest_id', '=', self.source_location_id.id),
                 ('product_id', '=', product.product_id.id),
                 ('lot_id', 'in', product.lot_ids.mapped('lot_id').ids),
                 ('state', 'in', ['done'])]).filtered(lambda sml: sml.move_id and sml.move_id.picking_id)
            for available_move in set(available_move_lines.mapped('move_id').filtered(lambda ml: ml.remaining_qty)):
                available_moves_to_be_returned.append(
                    {'move': available_move, 'move_lines': available_move_lines.filtered(
                        lambda m: m.move_id.id == available_move.id)})
        return available_moves_to_be_returned

    def get_all_move_vals_for_new_picking(self, product, location_id, available_moves):
        availability = product.quantity
        returned_moves = []
        all_move_vals = []
        if product.product_id.tracking == 'none':
            for available_move in available_moves:
                if available_move['move'].remaining_qty <= availability:
                    quantity = available_move['move'].remaining_qty
                else:
                    quantity = availability
                cost = available_move['move'].remaining_value / available_move['move'].remaining_qty

                returned_moves.append({'move_id': available_move, 'values': {'quantity': quantity,
                                                                             'cost': cost}})
                availability -= quantity
                if availability <= 0.0:
                    break

            for returned_move in returned_moves:
                move_vals = {
                    'product_id': product.product_id.id,
                    'name': product.product_id.name,
                    'product_uom': product.product_id.uom_id.id,
                    'product_uom_qty': returned_move['values']['quantity'],
                    'price_unit': returned_move['values']['cost'],
                    'value': returned_move['values']['cost'] * returned_move['values']['quantity'],
                }
                all_move_vals.append((0, 0, move_vals))
        elif product.product_id.tracking == 'serial':
            returned_moves = []
            availability = product.quantity
            for available_move in available_moves:
                cost = available_move['move'].remaining_value / available_move['move'].remaining_qty
                quantity = sum(line.qty_done for line in available_move['move_lines'])
                location_id = available_move['move'].picking_id.location_id

                returned_moves.append({'move_id': available_move, 'values': {'quantity': quantity,
                                                                             'cost': cost}})
                availability -= quantity
                if availability <= 0.0:
                    break

            for returned_move in returned_moves:
                move_line_copies = returned_move['move_id']['move_lines'].filtered(
                    lambda l: l.lot_id and l.lot_id in product.lot_ids.mapped('lot_id'))

                move_line_ids = []
                for move_line in move_line_copies:
                    move_line_vals = {'product_id': product.product_id.id,
                                      'product_uom_id': product.product_id.uom_id.id,
                                      'product_uom_qty': move_line.qty_done,
                                      'qty_done': move_line.qty_done,
                                      'lot_id': move_line.lot_id.id,
                                      'lot_name': move_line.lot_id.name,
                                      'location_id': location_id.id,
                                      'location_dest_id': self.destination_location_id.id,
                                      }
                    move_line_ids.append((0, 0, move_line_vals.copy()))
                move_vals = {
                    'product_id': product.product_id.id,
                    'name': product.product_id.name,
                    'product_uom': product.product_id.uom_id.id,
                    'product_uom_qty': returned_move['values']['quantity'],
                    'price_unit': returned_move['values']['cost'],
                    'value': returned_move['values']['cost'] * returned_move['values']['quantity'],
                    'move_line_ids': move_line_ids,
                }
                all_move_vals.append((0, 0, move_vals.copy()))

        return all_move_vals

    def get_all_picking_to_be_returned(self, all_picking_to_be_returned, product, available_moves):
        availability = product.quantity

        if product.product_id.tracking == 'none':
            for available_move in available_moves:
                if available_move['move'].remaining_qty <= availability:
                    quantity = available_move['move'].remaining_qty
                else:
                    quantity = availability
                product_return_moves_vals = {'product_id': product.product_id.id,
                                             'quantity': quantity,
                                             'move_id': available_move['move'].id,
                                             'uom_id': available_move['move'].product_id.uom_id.id}
                return_location_id = available_move['move'].picking_id.location_id

                if all_picking_to_be_returned:

                    if available_move['move'].picking_id.id not in all_picking_to_be_returned.keys():
                        all_picking_to_be_returned[available_move['move'].picking_id.id] = {
                            'picking_id': available_move['move'].picking_id.id,
                            'location_id': return_location_id.id,
                            'product_return_moves': [(0, 0, product_return_moves_vals)]}
                    else:
                        all_picking_to_be_returned[available_move['move'].picking_id.id]['product_return_moves'].append(
                            (0, 0, product_return_moves_vals))

                else:
                    all_picking_to_be_returned[available_move['move'].picking_id.id] = {
                        'picking_id': available_move['move'].picking_id.id,
                        'location_id': return_location_id.id,
                        'product_return_moves': [(0, 0, product_return_moves_vals)]}

                availability -= quantity
                if availability <= 0.0:
                    break
        elif product.product_id.tracking == 'serial':
            for available_move in available_moves:
                quantity = sum(line.qty_done for line in available_move['move_lines'])

                product_return_moves_vals = {'product_id': product.product_id.id,
                                             'quantity': quantity,
                                             'move_id': available_move['move'].id,
                                             'uom_id': available_move['move'].product_id.uom_id.id}
                location_id = available_move['move'].picking_id.location_id

                if available_move['move'].picking_id.id not in all_picking_to_be_returned.keys():
                    all_picking_to_be_returned[available_move['move'].picking_id.id] = {
                        'picking_id': available_move['move'].picking_id.id,
                        'location_id': location_id.id,
                        'product_lots': {product.product_id: {
                            available_move['move'].id: available_move['move_lines'].mapped('lot_id').ids}},
                        'product_return_moves': [(0, 0, product_return_moves_vals)]}
                else:
                    all_picking_to_be_returned[available_move['move'].picking_id.id]['product_return_moves'].append(
                        (0, 0, product_return_moves_vals))

                    if all_picking_to_be_returned[available_move['move'].picking_id.id].get('product_lots'):
                        if all_picking_to_be_returned[available_move['move'].picking_id.id]['product_lots'].get(
                                product.product_id):
                            all_picking_to_be_returned[available_move['move'].picking_id.id]['product_lots'][
                                product.product_id][available_move['move'].id] = available_move['move_lines'].mapped(
                                'lot_id').ids
                        else:
                            all_picking_to_be_returned[available_move['move'].picking_id.id]['product_lots'][
                                product.product_id] = {
                                available_move['move'].id: available_move['move_lines'].mapped(
                                    'lot_id').ids}

                    else:
                        all_picking_to_be_returned[available_move['move'].picking_id.id]['product_lots'] = {
                            product.product_id: {
                                available_move['move'].id: available_move['move_lines'].mapped('lot_id').ids}}

                availability -= quantity
                if availability <= 0.0:
                    break

        return all_picking_to_be_returned

    @api.multi
    def do_transfer(self):
        for record in self:
            # Validation
            if not record.product_ids:
                raise ValidationError(_("There is no products to transfer"))
            in_picking_type_id = self.env.user.company_id.internal_receipt_id
            return_picking_type_id = self.env.user.company_id.return_picking_type_id
            if not in_picking_type_id or not return_picking_type_id:
                raise ValidationError(_("There is no Picking Types for internal transfer"))

            all_move_vals = []
            all_picking_to_be_returned = {}
            customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            for product in record.product_ids:
                available_moves = self.get_product_available_moves(product)
                all_move_vals += self.get_all_move_vals_for_new_picking(product, location_id, available_moves)
                all_picking_to_be_returned.update(
                    self.get_all_picking_to_be_returned(all_picking_to_be_returned, product, available_moves))

            returned_picking_list = self.create_return_pickings(all_picking_to_be_returned, return_picking_type_id)
            new_picking_list = self.create_receipt_new_picking(in_picking_type_id, location_id, all_move_vals)
            self.state = 'transferred'

            return {
                'domain': [('id', 'in', new_picking_list)],
                'name': 'Picking',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
            }

    def _fifo_create_returns(self, stock_picking_return, location_id, picking_id, return_picking_type_id):
        for return_move in stock_picking_return.product_return_moves.mapped('move_id'):
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

        # create new picking for returned products
        picking_type_id = return_picking_type_id.id
        picking_id = self.env['stock.picking'].browse(picking_id)
        new_picking = picking_id.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'state': 'draft',
            'origin': picking_id.name,
            'location_id': picking_id.location_dest_id.id,
            'location_dest_id': location_id})
        new_picking.message_post_with_view('mail.message_origin_link',
                                           values={'self': new_picking, 'origin': picking_id},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        for return_line in stock_picking_return.product_return_moves:
            if return_line.quantity:
                vals = stock_picking_return._prepare_move_default_values(return_line, new_picking)
                r = return_line.move_id.copy(vals)
                vals = {}
                move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link | return_line.move_id]
                vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                r.write(vals)
        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking.id, picking_type_id

    def create_return_pickings(self, all_picking_to_be_returned, return_picking_type_id):
        returned_picking_list = []
        # Create return Picking For all Products
        for picking_return_vals in all_picking_to_be_returned.values():
            product_lots = picking_return_vals.get('product_lots').copy() if picking_return_vals.get(
                'product_lots') else {}
            if picking_return_vals.get('product_lots'):
                del picking_return_vals['product_lots']
            stock_picking_return = self.env['stock.return.picking'].create(picking_return_vals)

            if stock_picking_return:
                return_pick_list = self._fifo_create_returns(stock_picking_return, picking_return_vals['location_id'],
                                                             picking_return_vals['picking_id'], return_picking_type_id)
                return_pick = self.env['stock.picking'].browse(return_pick_list[0])
                if return_pick:
                    # # Validate new picking
                    for return_pick_move in return_pick.move_lines.filtered(
                            lambda m: m.state not in ['done', 'cancel']):
                        if return_pick_move.product_id.tracking == 'none':
                            for return_move_line in return_pick_move.move_line_ids:
                                return_move_line.qty_done = return_move_line.product_uom_qty
                        elif return_pick_move.product_id.tracking == 'serial':
                            product_return_lots = product_lots[return_pick_move.product_id]
                            i = 0
                            for return_move_line in return_pick_move.move_line_ids:
                                return_move_line.lot_id = \
                                    product_return_lots[return_move_line.move_id.move_orig_ids[0].id][i]
                                return_move_line.qty_done = return_move_line.product_uom_qty
                                i += 1

                    return_pick.action_done()
                returned_picking_list.append(return_pick)

        for product in self.product_ids:
            product_lots = set([lot.lot_id for lot in product.lot_ids])
            returned_lots = set([move_line.lot_id for picking in returned_picking_list
                                 if picking.state == 'done' for move in picking.move_lines.filtered(
                    lambda m: m.state == 'done' and m.product_id.id == product.product_id.id) for move_line in
                                 move.move_line_ids])

            not_available_lots = product_lots - returned_lots

            if not_available_lots:
                raise ValidationError(_("There is no available quantity For those lots {}".format(
                    [lot.name for lot in not_available_lots])))
        # print("//////////// returned_picking_list", returned_picking_list)
        return returned_picking_list

    def create_receipt_new_picking(self, in_picking_type_id, location_id, all_move_vals):
        new_picking_list = []
        new_picking_vals = {
            'picking_type_id': in_picking_type_id.id,
            'location_id': location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'move_lines': all_move_vals,
        }
        new_picking = self.env['stock.picking'].create(new_picking_vals)
        if new_picking:
            new_picking.action_confirm()
            new_picking.action_assign()
            for move in new_picking.move_lines.filtered(
                    lambda m: m.state not in ['done', 'cancel']):

                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            new_picking.action_done()
            new_picking_list.append(new_picking.id)
        return new_picking_list


