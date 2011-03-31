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
"Balances Accounting"
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from decimal import Decimal
import datetime

#
# Остатки по счетам за периоды
#
class BalanceAccount(ModelSQL, ModelView):
    _name = "ekd.balances.account"

    def __init__(self):
        super(BalanceAccount, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def post_balance(self, values=None):
        '''
        Изменение остатка и оборота в учетном регистре счета
        values = {'company': ID учетной организации,
                  'period': ID периода,
                  'account': ID счета,
                  'transfer': ID счета,
                  'debit': Сумма,
                  'credit': Сумма,
                  }
        '''
        if values == None:
            return False

        # kind - balance accounting period
        # kind - off_balance_out - outside of accounting period
        if values.get('account_kind', 'balance') == 'off_balance_out':
            balance_id = self.search([
                        ('account','=', values.get('account')),
                        ], limit=1)
        else:
            balance_id = self.search([
                        ('period','=',values.get('period').id),
                        ('account','=', values.get('account')),
                        ], limit=1)

        if balance_id:
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state =='done':
                self.raise_user_error('balance_account_done')

            cr = Transaction().cursor
            if values.get('debit'):
                cr.execute("UPDATE ekd_balances_account "\
                        " SET debit = debit+%s, write_date='%s' "%\
                        (values.get('debit'), datetime.datetime.now())+\
                        " WHERE id=%s"%balance_id)
            elif values.get('credit'):
                cr.execute("UPDATE ekd_balances_account "\
                        " SET credit = credit+%s, write_date='%s' "%\
                        (values.get('credit'), datetime.datetime.now())+\
                        " WHERE id=%s"%balance_id)

            if balance.transfer and values.get('transfer', True):
                self.transfer_balance(balance.transfer.id, {
                            'balance_dt':balance.balance_dt_end,
                            'balance_ct':balance.balance_ct_end,
                            'transfer': values.get('transfer', True),
                            })
        else:
            if values.get('account_kind', 'balance') == 'off_balance_out':
                balance_id = self.create({
                        'account': values.get('account'),
                        'balance_dt': Decimal('0.0'),
                        'balance_ct': Decimal('0.0'),
                        'debit': values.get('debit', Decimal('0.0')),
                        'credit': values.get('credit', Decimal('0.0')),
                        })
            else:
                period_prev = values.get('period').search([
                        ('company','=',values.get('company')),
                        ('end_date','<',values.get('date_operation')),
                        ], order=[('end_date','DESC')], limit=1)

                balance_prev={}
                for direct in ['dt','ct']:
                    balance_prev.setdefault(direct, Decimal('0.0'))
                if len(period_prev) and isinstance(period_prev, list):
                    period_prev = period_prev[0]

                balance_prev_id = self.search([
                            ('period','=', period_prev),
                            ('account','=', values.get('account')),
                            ], limit=1)
                for bal_prev in self.browse(balance_prev_id):
                    balance_prev['dt'] = bal_prev.balance_dt_end
                    balance_prev['ct'] = bal_prev.balance_ct_end
                balance_id = self.create({
                        'company': values.get('company'),
                        'period': values.get('period'),
                        'account': values.get('account'),
                        'balance_dt': balance_prev['dt'],
                        'balance_ct': balance_prev['ct'],
                        'debit': values.get('debit', Decimal('0.0')),
                        'credit': values.get('credit', Decimal('0.0')),
                        })

            if balance_prev_id:
                self.write(balance_prev_id, {
                        'transfer': balance_id,
                        })

        return balance_id

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {'company': ID учетной организации,
                  'date_operation': Дата операции,
                  'dt_account': ID счета,
                  'ct_account': ID счета,
                  'amount': Дебет, }
        '''
        if values == None:
            return False

        if values.get('account_kind', 'balance') == 'off_balance_out':
            balance_id = self.search([
                        ('account','=', values.get('account')),
                        ], limit=1)
        else:
            if values.get('balance_id') and values.get('balance_id') > 0:
                balance_id = values.get('balance_id')
            else:
                balance_id = self.search([
                        ('period','=',values.get('period').id),
                        ('account','=', values.get('account').id),
                        ], limit=1)

        if balance_id:
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state == 'done':
                self.raise_user_error('balance_account_done')

            #self.write(balance_id, {
            #            'debit': balance.debit-values.get('debit', Decimal('0.0')),
            #            'credit': balance.credit-values.get('credit', Decimal('0.0')),
            #            })
            cr = Transaction().cursor
            if values.get('debit'):
                cr.execute("UPDATE "+self._table+\
                    " SET debit = debit-%s, write_date='%s' "%(values.get('debit'), datetime.datetime.now())+\
                    " WHERE id = %s "%balance_id)
            elif values.get('credit'):
                cr.execute("UPDATE "+self._table+\
                    " SET credit = credit-%s, write_date='%s' "%(values.get('credit'), datetime.datetime.now())+\
                    " WHERE id = %s "%balance_id)

            if balance.transfer and values.get('transfer',True):
                self.transfer_balance(balance.transfer.id, {
                            'balance_dt':balance.balance_dt_end,
                            'balance_ct':balance.balance_ct_end,
                            'transfer': values.get('transfer',True)
                            })
        else:
            raise Exception(str(balance_id), str(values))
            self.raise_user_error('balance_account_not_find')

        return balance_id

BalanceAccount()

#
# Остатки по финансовым счетам за периоды 
#
class BalanceFinance(ModelSQL, ModelView):
    _name = "ekd.balances.finance"

    def __init__(self):
        super(BalanceFinance, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Finance Balance Account is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def post_balance(self, values=None):
        '''
        Изменение остатка и оборота в учетном регистре счета
        values = {'company': ID учетной организации,
                  'date_operation': Дата операции,
                  'account': ID счета,
                  'debit': сумма, }
                  'credit': сумма, }
        '''
        if values == None:
            return False

        balance_id = self.search([
                        ('date_balance','=',values.get('date_operation').strftime('%Y-%m-%d')),
                        ('account','=', values.get('account').id),
                        ], limit=1)
        #raise Exception(str(balance_id), values.get('date_operation').strftime('%Y-%m-%d'), str(values.get('account').id))


        if balance_id:
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state =='done':
                self.raise_user_error('balance_account_done')

            self.write(balance_id, {
                        'debit': balance.debit+values.get('debit', Decimal('0.0')),
                        'credit': balance.credit+values.get('credit', Decimal('0.0')),
                        })
            if balance.transfer and values.get('transfer',True):
                self.transfer_balance(balance.transfer.id, {
                            'balance': balance.balance_end,
                            'transfer': values.get('transfer',True)
                            })
        else:
            balance_prev_id = self.search([
                        ('date_balance','<',values.get('date_operation')),
                        ('account','=', values.get('account')),
                        ], order=[('date_balance','DESC')], limit=1)

            balance_prev = Decimal('0.0')
            for balance_pre in self.browse(balance_prev_id):
                balance_prev =  balance_pre.balance_end
            balance_id = self.create({
                        'company': values.get('company'),
                        'date_balance': values.get('date_operation'),
                        'account': values.get('account'),
                        'balance': balance_prev,
                        'debit': values.get('debit', Decimal('0.0')),
                        'credit': values.get('credit', Decimal('0.0')),
                        })

            if balance_prev_id:
                self.write(balance_prev_id, {
                        'transfer': balance_id,
                        })

        return balance_id

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {'company': ID учетной организации,
                  'date_operation': Дата операции,
                  'account': ID счета,
                  'debit': Дебет, }
                  'credit': Кредит, }
        '''
        if values == None:
            return False
        if values.get('balance_id') and values.get('balance_id') > 0:
            balance_id = values.get('balance_id')
        else:
            balance_id = self.search([
                        ('date_balance','=',values.get('date_operation').strftime('%Y-%m-%d')),
                        ('account','=', values.get('account').id),
                        ], limit=1)
            #raise Exception(str(balance_id), str(values.get('account').id), values.get('date_operation').strftime('%Y-%m-%d'))


        if balance_id:
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state =='done':
                self.raise_user_error('balance_account_done')

            self.write(balance_id, {
                        'debit': balance.debit-values.get('debit', Decimal('0.0')),
                        'credit': balance.credit-values.get('credit', Decimal('0.0'))
                        })
            if balance.transfer and values.get('transfer',True):
                self.transfer_balance(balance.transfer.id, {
                            'balance': balance.balance_end,
                            'transfer': values.get('transfer',True)
                            })
        else:
            #raise Exception(str(values))
            self.raise_user_error('balance_account_not_find')

        return balance_id

BalanceFinance()
