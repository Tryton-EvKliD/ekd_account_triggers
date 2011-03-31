# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
##############################################################################
# В данном файле описываются объекты 
# 3. Тип счетов
# 3. Остатки по счетам
# 3. 
# 3. 
##############################################################################
#UPDATE account_ru_book_cash_test
#   SET debit=debit+12, credit=credit-10
#    WHERE reference in ('111,22', '333,33');
"Balances Accounting Party"
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from decimal import Decimal
import datetime

#
# Остатки по счетам за периоды (Дебиторская и кредиторская задолжность)
#
class BalancePartner(ModelSQL, ModelView):
    _name = "ekd.balances.party"

    def __init__(self):
        super(BalancePartner, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def post_balance(self, values=None):
        '''
        Изменение остатка и оборота в учетном регистре счета
        values = {
                      'period': BrowseRecord(Учетный период)
                      'account': BrowseRecord(ID счета),
                      'analytic': [{
                            'id': ID строки
                            'level': Уровень аналитики,
                            'model_ref': модель и ID,
                                   },...],строк
                      'debit': Сумма,
                      'credit': Сумма, 
                }
        '''
        if values == None or not values.get('analytic', False):
            return {}
        party_period_obj = self.pool.get('ekd.balances.party.period')
        #party_year_obj = self.pool.get('ekd.balances.party.year')
        party_period_create = party_period_obj.create
        res={}
        need_actived=False
        search_find = {}
        search_not_find = {}
        level_find={}
        level_not_find=[]
        amount_ids=[]
        level_sort = {}
        if len(values.get('analytic')) >= 1:
            for line_analytic in values.get('analytic'):
                level_sort[line_analytic.get('level')]=line_analytic.get('id')
                if line_analytic.get('level') == '01':
                    analytic_id = self.search([
                            ('account','=', values.get('account').id),
                            ('level','=','01'),
                            ('model_ref','=',line_analytic.get('model_ref')),
                            ], limit=1)
                    if isinstance(analytic_id, list) and analytic_id:
                        analytic_id = analytic_id[0]
                    if analytic_id:
                        search_find[analytic_id] = line_analytic.get('id')
                        last_id = analytic_id
                        level_find[line_analytic.get('level')] = analytic_id
                    else:
                        level_not_find.append(line_analytic.get('level'))
                        search_not_find[line_analytic.get('id')] = {
                            'account': values.get('account').id,
                            'level': line_analytic.get('level'),
                            'model_ref': line_analytic.get('model_ref'),
                            }
                elif search_not_find:
                    level_not_find.append(line_analytic.get('level'))
                    search_not_find[line_analytic.get('id')] = {
                            'account': values.get('account').id,
                            'level': line_analytic.get('level'),
                            'model_ref': line_analytic.get('model_ref'),
                            }
                else:
                    analytic_id = self.search([
                            ('account','=', values.get('account').id),
                            ('level','=',line_analytic.get('level')),
                            ('model_ref','=',line_analytic.get('model_ref')),
                            ('parent','=', last_id),
                            ], limit=1)
                    if isinstance(analytic_id, list) and len(analytic_id)>0:
                        analytic_id = analytic_id[0]
                    if analytic_id:
                        last_id = analytic_id
                        search_find[analytic_id] = line_analytic.get('id')
                        level_find[line_analytic.get('level')] = analytic_id
                    else:
                        level_not_find.append(line_analytic.get('level'))
                        search_not_find[line_analytic.get('id')] = {
                            'account': values.get('account').id,
                            'level': line_analytic.get('level'),
                            'model_ref': line_analytic.get('model_ref'),
                            'parent': last_id,
                            }
        else:
            raise Exception(str(values))
            search_find[line_analytic.get('id')] = self.search([
                            ('account','=', values.get('account').id),
                            ('level','=',values.get('analytic').get('level')),
                            ('model_ref','=',values.get('analytic').get('model_ref')),
                            ], limit=1)
        analytic_id = False
        if search_find:
            for analytic in self.browse([ x[1] for x in sorted(level_find.items(),key=lambda x:x[0])]):
                if analytic.state =='done':
                    self.raise_user_error('balance_account_done')
                if not analytic.active:
                    need_actived=True
                if analytic.curr_period and analytic.curr_period.period.id == values.get('period').id:
                    amount_id = analytic.curr_period.id
                    amount_ids.append(amount_id)
                elif analytic.last_period and analytic.last_period.period.id == values.get('period').id:
                    amount_id = analytic.last_period.id
                    amount_ids.append(amount_id)
                else:
                    amount_id = party_period_obj.search([
                            ('account','=',analytic.id),
                            ('period','=', values.get('period').id),
                            ])
                    if isinstance(amount_id, list) and len(amount_id)>0:
                        amount_id = amount_id[0]
                    if amount_id:
                        amount_ids.append(amount_id)
                    else:
                        if analytic.amount_periods[0]:
                            parent = analytic.amount_periods[0].id
                        if values.get('debit'):
                            amount_id = party_period_obj.create({
                                'account': analytic.id,
                                'period': values.get('period').id,
                                'debit': values.get('debit'),
                                'parent': parent,
                                })
                        else:
                            amount_id = party_period_create({
                                'account': analytic.id,
                                'period': values.get('period').id,
                                'credit': values.get('credit'),
                                'parent': parent,
                                })
                        party_period_obj.write(parent, {
                            'transfer': amount_id,
                            })
                        self.write(analytic.id, {'curr_period':amount_id})
                analytic_id = analytic.id
                res[search_find.get(analytic.id)] = [analytic_id, amount_id]
            if amount_ids:
                cr = Transaction().cursor
                if values.get('debit'):
                    cr.execute("UPDATE ekd_balances_party_period "\
                            " SET debit = debit+%s, write_date='%s' "%\
                            (values.get('debit'), datetime.datetime.now())+\
                            " WHERE id in("+",".join(map(str, amount_ids))+")")
                elif values.get('credit'):
                    cr.execute("UPDATE ekd_balances_party_period "\
                            " SET credit = credit+%s, write_date='%s' "%\
                            (values.get('credit'), datetime.datetime.now())+\
                            " WHERE id in("+",".join(map(str, amount_ids))+")")

        if search_not_find:
            level_not_find.sort()
            for level in level_not_find:
                if not search_not_find.get(level_sort[level]).get('parent'):
                    search_not_find.get(level_sort[level])['parent'] = analytic_id
                analytic_id = self.create(search_not_find.get(level_sort[level]))
                #raise Exception(str(search_not_find))
                if values.get('debit'):
                    amount_id = party_period_create({
                            'account': analytic_id,
                            'period': values.get('period').id,
                            'debit': values.get('debit'),
                            })
                else:
                    amount_id = party_period_create({
                            'account': analytic_id,
                            'period': values.get('period').id,
                            'credit': values.get('credit'),
                            })
                self.write(analytic_id, {'curr_period':amount_id})
                res[level_sort[level]] = [analytic_id, amount_id]
                
        return res

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
            values = {
                'company':move.company.id,
                'period':period_id,
                'account':line.ct_account.id,
                'analytic': [{
                    'id': ID строки
                    'level': Уровень аналитики,
                    'model_ref': модель и ID,
                    'balance_party': ID Analytic Account (Party),
                    'period_party': ID line period amount,
                    },...],строк
                'debit': line.amount,
                'credit': line.amount,
                }
        '''
        if values == None:
            return False

        if not values.get('analytic', False):
            return None
            raise Exception("Don't find analytic %s"%(values))

        cr = Transaction().cursor
        if values.get('debit'):
            cr.execute("UPDATE ekd_balances_party_period "\
                    " SET debit = debit-%s, write_date='%s' "%(values.get('debit'), datetime.datetime.now())+\
                    " WHERE id in("+",".join(str(x.ref_period) for x in values.get('analytic'))+")")
        elif values.get('credit'):
            #raise Exception(str(values))
            cr.execute("UPDATE ekd_balances_party_period     "\
                    " SET credit = credit-%s, write_date='%s' "%(values.get('credit'), datetime.datetime.now())+\
                    " WHERE id in("+",".join(str(x.ref_period) for x in values.get('analytic'))+")")
        #else:
        #    raise Exception('Error values', str(values) )

        #if balance.transfer and values.get('transfer',True):
        #    self.transfer_balance(balance.transfer.id, {
        #                'balance_dt':balance.balance_dt_end,
        #                'balance_ct':balance.balance_ct_end,
        #                'transfer': values.get('transfer',True)
        #                })

        return values.get('balance_id')

BalancePartner()

