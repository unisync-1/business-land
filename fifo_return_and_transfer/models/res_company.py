# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):

    _inherit = "res.company"

    return_picking_type_id = fields.Many2one(comodel_name="stock.picking.type",
                                             string="Internal Transfer With Cost Return Type")
    internal_receipt_id = fields.Many2one(comodel_name="stock.picking.type",
                                          string="Internal Transfer With Cost Receipt Type")


