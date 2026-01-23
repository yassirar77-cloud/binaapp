'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import './transactions.css';

interface Transaction {
  transaction_id: string;
  transaction_type: string;
  item_description: string;
  amount: number;
  payment_status: string;
  created_at: string;
  toyyibpay_bill_code?: string;
  invoice_number?: string;
  metadata?: Record<string, any>;
}

interface TransactionsResponse {
  transactions: Transaction[];
  total_spent: number;
  count: number;
}

export default function TransactionsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalSpent, setTotalSpent] = useState(0);
  const [filter, setFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  useEffect(() => {
    fetchTransactions();
  }, [filter, dateFrom, dateTo]);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const token = getStoredToken();

      if (!token) {
        router.push('/login');
        return;
      }

      let url = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/transactions?limit=100`;

      if (filter && filter !== 'all') {
        url += `&transaction_type=${filter}`;
      }
      if (dateFrom) {
        url += `&from_date=${dateFrom}`;
      }
      if (dateTo) {
        url += `&to_date=${dateTo}`;
      }

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data: TransactionsResponse = await response.json();
        setTransactions(data.transactions || []);
        setTotalSpent(data.total_spent || 0);
      }
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ms-MY', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; class: string }> = {
      success: { label: 'Berjaya', class: 'status-success' },
      pending: { label: 'Menunggu', class: 'status-pending' },
      failed: { label: 'Gagal', class: 'status-failed' }
    };

    const statusInfo = statusMap[status] || { label: status, class: 'status-default' };

    return (
      <span className={`status-badge ${statusInfo.class}`}>
        {statusInfo.label}
      </span>
    );
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      subscription: '',
      renewal: '',
      addon: ''
    };
    return icons[type] || '';
  };

  const exportCSV = () => {
    if (transactions.length === 0) return;

    const headers = ['Tarikh', 'Penerangan', 'Jenis', 'Jumlah (RM)', 'Status'];
    const rows = transactions.map(tx => [
      formatDate(tx.created_at),
      tx.item_description,
      tx.transaction_type,
      tx.amount.toFixed(2),
      tx.payment_status
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `binaapp-transaksi-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="transactions-page">
      <div className="transactions-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => router.back()}>
            &larr; Kembali
          </button>
          <h1>Sejarah Transaksi</h1>
        </div>
        <button className="export-btn" onClick={exportCSV} disabled={transactions.length === 0}>
          Eksport CSV
        </button>
      </div>

      <div className="transactions-summary">
        <div className="summary-card">
          <span className="summary-label">Jumlah Perbelanjaan</span>
          <span className="summary-value">RM {totalSpent.toFixed(2)}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Jumlah Transaksi</span>
          <span className="summary-value">{transactions.length}</span>
        </div>
      </div>

      <div className="transactions-filters">
        <div className="filter-group">
          <label>Jenis</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">Semua</option>
            <option value="subscription">Langganan</option>
            <option value="renewal">Pembaharuan</option>
            <option value="addon">Addon</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Dari</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Hingga</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        <button
          className="clear-filters-btn"
          onClick={() => {
            setFilter('all');
            setDateFrom('');
            setDateTo('');
          }}
        >
          Padam Tapis
        </button>
      </div>

      <div className="transactions-table-container">
        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <p>Memuatkan transaksi...</p>
          </div>
        ) : transactions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">&#128203;</div>
            <h3>Tiada Transaksi</h3>
            <p>Anda belum mempunyai sebarang transaksi lagi.</p>
          </div>
        ) : (
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Tarikh</th>
                <th>Penerangan</th>
                <th>Jumlah</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.transaction_id}>
                  <td className="date-cell">
                    <span className="date">{formatDate(tx.created_at)}</span>
                  </td>
                  <td className="description-cell">
                    <span className="type-icon">{getTypeIcon(tx.transaction_type)}</span>
                    <div className="description-text">
                      <span className="description">{tx.item_description}</span>
                      <span className="type-badge">{tx.transaction_type}</span>
                    </div>
                  </td>
                  <td className="amount-cell">
                    <span className="amount">RM {tx.amount.toFixed(2)}</span>
                  </td>
                  <td className="status-cell">
                    {getStatusBadge(tx.payment_status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {transactions.length > 0 && (
        <div className="transactions-footer">
          <p>Menunjukkan {transactions.length} transaksi</p>
        </div>
      )}
    </div>
  );
}
