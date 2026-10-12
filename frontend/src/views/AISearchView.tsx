import React, { useState } from 'react';
import {
  Search,
  ShieldCheck,
  AlertCircle,
  Lightbulb,
  BookOpen,
  Globe,
  Layers,
  ExternalLink,
  Copy,
  Check,
  RotateCcw,
  AlertTriangle,
  Sliders,
  ChevronDown,
  ChevronUp,
  Download,
  Info,
  Eye,
  Loader2,
  X,
  FileText
} from 'lucide-react';
import type { Course, AISearchResult, SearchMode, ResearchDepth, FreshnessPreference } from '../types';
import { api } from '../api';
import { openProtectedMaterial, downloadProtectedMaterial } from '../utils/materialViewer';

interface AISearchViewProps {
  courses: Course[];
  initialCourseId?: number;
}

// Simple and safe Markdown content renderer for university LMS answers
const RenderMarkdownContent: React.FC<{ content: string }> = ({ content }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];
  let tableRows: string[] = [];
  let inTable = false;

  const flushTable = (key: number) => {
    if (tableRows.length === 0) return null;
    const rows = [...tableRows];
    tableRows = [];
    inTable = false;

    const parsed = rows
      .map((r) =>
        r
          .split('|')
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
      )
      .filter((r) => r.length > 0 && !r.every((c) => /^[-:]+$/.test(c)));

    if (parsed.length === 0) return null;
    const headers = parsed[0];
    const data = parsed.slice(1);

    return (
      <div key={`table-${key}`} style={{ overflowX: 'auto', margin: '14px 0' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f1f5f9' }}>
              {headers.map((h, i) => (
                <th key={i} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, border: '1px solid #e2e8f0', color: '#1e293b' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rIdx) => (
              <tr key={rIdx} style={{ backgroundColor: rIdx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} style={{ padding: '8px 12px', border: '1px solid #e2e8f0', color: '#334155' }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const formatInline = (text: string): React.ReactNode => {
    // Bold formatting: **text**
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={idx} style={{ color: '#0f172a' }}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={idx}
            style={{
              backgroundColor: '#f1f5f9',
              padding: '2px 5px',
              borderRadius: '3px',
              fontSize: '12px',
              fontFamily: 'monospace',
              color: '#0f172a',
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block handling
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`code-${i}`}
            style={{
              backgroundColor: '#0f172a',
              color: '#f8fafc',
              padding: '12px 16px',
              borderRadius: '6px',
              fontSize: '12.5px',
              overflowX: 'auto',
              fontFamily: 'monospace',
              margin: '12px 0',
            }}
          >
            <code>{codeBuffer.join('\n')}</code>
          </pre>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // Markdown Table handling
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      inTable = true;
      tableRows.push(line);
      continue;
    } else if (inTable) {
      const tbl = flushTable(i);
      if (tbl) elements.push(tbl);
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h3
          key={`h3-${i}`}
          style={{
            fontSize: '14.5px',
            fontWeight: 700,
            color: '#1e3a8a',
            marginTop: '16px',
            marginBottom: '8px',
            borderBottom: '1px solid #e2e8f0',
            paddingBottom: '4px',
          }}
        >
          {line.replace('### ', '')}
        </h3>
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2
          key={`h2-${i}`}
          style={{
            fontSize: '16px',
            fontWeight: 700,
            color: '#0f172a',
            marginTop: '18px',
            marginBottom: '8px',
          }}
        >
          {line.replace('## ', '')}
        </h2>
      );
    } else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      // Bullet list items
      elements.push(
        <li
          key={`li-${i}`}
          style={{
            fontSize: '13.5px',
            lineHeight: 1.65,
            color: '#334155',
            marginLeft: '18px',
            marginBottom: '4px',
          }}
        >
          {formatInline(line.trim().replace(/^[-*]\s+/, ''))}
        </li>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={`blank-${i}`} style={{ height: '8px' }} />);
    } else {
      elements.push(
        <p
          key={`p-${i}`}
          style={{
            fontSize: '13.5px',
            lineHeight: 1.65,
            color: '#1e293b',
            marginBottom: '6px',
          }}
        >
          {formatInline(line)}
        </p>
      );
    }
  }

  if (inTable) {
    const tbl = flushTable(lines.length);
    if (tbl) elements.push(tbl);
  }

  return <div>{elements}</div>;
};

export const AISearchView: React.FC<AISearchViewProps> = ({
  courses,
  initialCourseId,
}) => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('course_notes');
  const [depth, setDepth] = useState<ResearchDepth>('standard');
  const [freshness, setFreshness] = useState<FreshnessPreference>('any');
  const [selectedCourseId, setSelectedCourseId] = useState<number | undefined>(initialCourseId);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AISearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Authenticated Material Access States
  const [activeMaterialAction, setActiveMaterialAction] = useState<{ materialId: number; type: 'open' | 'download' } | null>(null);
  const [materialFeedback, setMaterialFeedback] = useState<{ text: string; isError: boolean } | null>(null);
  const [previewTextModal, setPreviewTextModal] = useState<{ title: string; content: string } | null>(null);

  const handleOpenMaterial = async (courseId: number, materialId: number, title: string) => {
    setActiveMaterialAction({ materialId, type: 'open' });
    setMaterialFeedback(null);
    try {
      const res = await openProtectedMaterial(
        courseId,
        materialId,
        title,
        (text, filename) => {
          setPreviewTextModal({ title: filename, content: text });
        }
      );
      if (res.action === 'DOWNLOADED') {
        setMaterialFeedback({ text: `Downloaded "${res.filename}" successfully.`, isError: false });
      }
    } catch (err: any) {
      setMaterialFeedback({ text: err.message || 'Failed to open material.', isError: true });
    } finally {
      setActiveMaterialAction(null);
    }
  };

  const handleDownloadMaterial = async (courseId: number, materialId: number, title: string) => {
    setActiveMaterialAction({ materialId, type: 'download' });
    setMaterialFeedback(null);
    try {
      const res = await downloadProtectedMaterial(courseId, materialId, title);
      setMaterialFeedback({ text: `Downloaded "${res.filename}" successfully.`, isError: false });
    } catch (err: any) {
      setMaterialFeedback({ text: err.message || 'Failed to download material.', isError: true });
    } finally {
      setActiveMaterialAction(null);
    }
  };

  // Normalization helper for modes
  const isClassNotes = mode === 'course_notes' || mode === 'COURSE_NOTES';
  const isWebResearch = mode === 'web_research' || mode === 'WEB_RESEARCH';
  const isBothSources = mode === 'hybrid' || mode === 'HYBRID';

  // Contextual question recommendations per mode
  const sampleQueries = {
    course_notes: [
      { text: 'Explain Dijkstra shortest path invariant and time complexity', course: 'CS201' },
      { text: 'How does Virtual Memory translate page tables using the TLB?', course: 'CS301' },
      { text: 'How does neural network backpropagation compute gradients with the chain rule?', course: 'CS401' },
      { text: "Explain mutexes, spinlocks, and Peterson's algorithm for mutual exclusion", course: 'CS301' },
    ],
    web_research: [
      { text: 'Compare PostgreSQL 17 vs PostgreSQL 18 memory and vector indexing features', course: 'Web' },
      { text: 'Compare React 19 Server Components architecture vs client-side SPAs', course: 'Web' },
      { text: 'What are current production best practices for FreeRTOS task scheduling in 2026?', course: 'Web' },
    ],
    hybrid: [
      { text: 'Compare Dijkstra algorithm taught in DSA with real-world road network routing engines', course: 'DSA + Web' },
      { text: 'How do operating system virtual memory page tables compare with modern hardware IOMMU?', course: 'OS + Web' },
    ],
  };

  const activeSamples = isClassNotes
    ? sampleQueries.course_notes
    : isWebResearch
      ? sampleQueries.web_research
      : sampleQueries.hybrid;

  const handleSearch = async (searchQueryText?: string, overrideMode?: SearchMode) => {
    const q = searchQueryText !== undefined ? searchQueryText : query;
    if (!q.trim()) return;

    const currentMode = overrideMode || mode;
    const isWeb = currentMode === 'web_research' || currentMode === 'WEB_RESEARCH';

    setLoading(true);
    setError(null);

    try {
      const res = await api.searchNotes({
        query: q.trim(),
        mode: currentMode,
        depth: depth,
        freshness: freshness,
        course_id: isWeb ? undefined : selectedCourseId,
        top_k: depth === 'quick' || depth === 'QUICK' ? 3 : depth === 'deep' || depth === 'DEEP' ? 6 : 4,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to complete research request. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyAnswerToClipboard = () => {
    if (!result) return;
    const textToCopy = `# Question: ${result.query}\n\n${result.answer}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const resetSearch = () => {
    setQuery('');
    setResult(null);
    setError(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Header Banner & Search Mode Selection */}
      <div
        className="card"
        style={{
          backgroundColor: '#1e3a8a', // Restrained Oxford Blue
          color: '#ffffff',
          padding: '24px 26px',
          border: 'none',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(30, 58, 138, 0.15)',
        }}
      >
        <div style={{ marginBottom: '18px' }}>
          <h1 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 6px 0', letterSpacing: '-0.01em', color: '#ffffff' }}>
            AI Research Assistant
          </h1>
          <p style={{ fontSize: '13px', color: '#cbd5e1', margin: 0, lineHeight: 1.4 }}>
            Ask a question. Get a clear answer from your course notes, the web, or both.
          </p>
        </div>

        {/* Three clearly labelled modes */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '18px' }}>
          {/* Mode 1: Class Notes */}
          <button
            type="button"
            onClick={() => setMode('course_notes')}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              textAlign: 'left',
              cursor: 'pointer',
              border: isClassNotes ? '2px solid #ffffff' : '1px solid rgba(255,255,255,0.25)',
              backgroundColor: isClassNotes ? '#ffffff' : 'rgba(255,255,255,0.08)',
              color: isClassNotes ? '#1e3a8a' : '#ffffff',
              transition: 'all 120ms ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontWeight: 700, fontSize: '13px', marginBottom: '3px' }}>
              <BookOpen size={15} color={isClassNotes ? '#1e3a8a' : '#93c5fd'} />
              <span>1. Class Notes</span>
            </div>
            <div style={{ fontSize: '11px', color: isClassNotes ? '#475569' : '#cbd5e1', lineHeight: 1.3 }}>
              Search uploaded course materials and lecture slides.
            </div>
          </button>

          {/* Mode 2: Web Research */}
          <button
            type="button"
            onClick={() => setMode('web_research')}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              textAlign: 'left',
              cursor: 'pointer',
              border: isWebResearch ? '2px solid #ffffff' : '1px solid rgba(255,255,255,0.25)',
              backgroundColor: isWebResearch ? '#ffffff' : 'rgba(255,255,255,0.08)',
              color: isWebResearch ? '#1e3a8a' : '#ffffff',
              transition: 'all 120ms ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontWeight: 700, fontSize: '13px', marginBottom: '3px' }}>
              <Globe size={15} color={isWebResearch ? '#1e3a8a' : '#93c5fd'} />
              <span>2. Web Research</span>
            </div>
            <div style={{ fontSize: '11px', color: isWebResearch ? '#475569' : '#cbd5e1', lineHeight: 1.3 }}>
              Search the live web for technical documentation and papers.
            </div>
          </button>

          {/* Mode 3: Both Sources */}
          <button
            type="button"
            onClick={() => setMode('hybrid')}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              textAlign: 'left',
              cursor: 'pointer',
              border: isBothSources ? '2px solid #ffffff' : '1px solid rgba(255,255,255,0.25)',
              backgroundColor: isBothSources ? '#ffffff' : 'rgba(255,255,255,0.08)',
              color: isBothSources ? '#1e3a8a' : '#ffffff',
              transition: 'all 120ms ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontWeight: 700, fontSize: '13px', marginBottom: '3px' }}>
              <Layers size={15} color={isBothSources ? '#1e3a8a' : '#93c5fd'} />
              <span>3. Both Sources</span>
            </div>
            <div style={{ fontSize: '11px', color: isBothSources ? '#475569' : '#cbd5e1', lineHeight: 1.3 }}>
              Combine your syllabus notes with live external web findings.
            </div>
          </button>
        </div>

        {/* Natural Language Question Field & Search Button */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            backgroundColor: '#ffffff',
            padding: '5px',
            borderRadius: '6px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
          }}
        >
          <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center' }}>
            <Search size={17} color="#64748b" style={{ position: 'absolute', left: '12px' }} />
            <input
              type="text"
              style={{
                width: '100%',
                border: 'none',
                outline: 'none',
                padding: '10px 12px 10px 38px',
                fontSize: '13.5px',
                color: '#0f172a',
                fontFamily: 'inherit',
              }}
              placeholder={
                isClassNotes
                  ? 'Ask a question from your course notes (e.g. Explain Dijkstra invariant and time complexity)...'
                  : isWebResearch
                    ? 'Search live technical papers, documentation, or release notes...'
                    : 'Compare course theory with live industry web findings...'
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            style={{
              padding: '0 22px',
              fontWeight: 600,
              fontSize: '13px',
              borderRadius: '4px',
              backgroundColor: '#1e3a8a',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {loading ? <span className="spinner" /> : <Search size={15} />}
            <span>{loading ? 'Searching...' : 'Search'}</span>
          </button>
        </div>

        {/* Controls Row: Course Selector & Advanced Options Toggle */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '12px',
            flexWrap: 'wrap',
            gap: '12px',
            fontSize: '12px',
          }}
        >
          {/* Course Scope Selector (for Class Notes & Both Sources) */}
          {!isWebResearch ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Filter by Course:</span>
              <select
                value={selectedCourseId || ''}
                onChange={(e) => setSelectedCourseId(e.target.value ? Number(e.target.value) : undefined)}
                style={{
                  padding: '4px 10px',
                  border: '1px solid rgba(255,255,255,0.3)',
                  borderRadius: '4px',
                  fontSize: '12px',
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  color: '#ffffff',
                  fontFamily: 'inherit',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                <option value="" style={{ color: '#0f172a' }}>All Enrolled Courses</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id} style={{ color: '#0f172a' }}>
                    {c.code} — {c.title.slice(0, 30)}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <span style={{ fontSize: '11.5px', color: '#93c5fd' }}>
              Searching live web sources across technical domains.
            </span>
          )}

          {/* Advanced Options Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              background: 'none',
              border: 'none',
              color: '#cbd5e1',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              fontSize: '12px',
              fontWeight: 500,
              padding: '4px 8px',
              borderRadius: '4px',
            }}
          >
            <Sliders size={13} />
            <span>Advanced Options</span>
            {showAdvanced ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {/* Collapsible Advanced Options Panel */}
        {showAdvanced && (
          <div
            style={{
              marginTop: '12px',
              padding: '12px 14px',
              backgroundColor: 'rgba(15, 23, 42, 0.45)',
              borderRadius: '6px',
              display: 'flex',
              gap: '20px',
              flexWrap: 'wrap',
              fontSize: '12px',
              border: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            {/* Depth Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Research Depth:</span>
              <div style={{ display: 'inline-flex', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px', padding: '2px' }}>
                {(['quick', 'standard', 'deep'] as ResearchDepth[]).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDepth(d)}
                    style={{
                      border: 'none',
                      padding: '3px 9px',
                      fontSize: '11px',
                      fontWeight: 600,
                      borderRadius: '3px',
                      cursor: 'pointer',
                      backgroundColor: depth === d ? '#ffffff' : 'transparent',
                      color: depth === d ? '#1e3a8a' : '#cbd5e1',
                      textTransform: 'capitalize',
                    }}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {/* Freshness Filter (for Web Research & Both Sources) */}
            {!isClassNotes && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Web Freshness:</span>
                <select
                  value={freshness}
                  onChange={(e) => setFreshness(e.target.value as FreshnessPreference)}
                  style={{
                    padding: '3px 8px',
                    border: '1px solid rgba(255,255,255,0.25)',
                    borderRadius: '4px',
                    fontSize: '11.5px',
                    backgroundColor: 'rgba(15, 23, 42, 0.6)',
                    color: '#ffffff',
                    fontFamily: 'inherit',
                    cursor: 'pointer',
                    outline: 'none',
                  }}
                >
                  <option value="any" style={{ color: '#0f172a' }}>Any Time</option>
                  <option value="day" style={{ color: '#0f172a' }}>Past 24 Hours</option>
                  <option value="week" style={{ color: '#0f172a' }}>Past Week</option>
                  <option value="month" style={{ color: '#0f172a' }}>Past Month</option>
                  <option value="year" style={{ color: '#0f172a' }}>Past Year (2025–2026)</option>
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 2. Suggested Example Questions (Mode-specific) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#64748b', fontWeight: 600 }}>
          <Lightbulb size={14} color="#b45309" />
          <span>Example questions for {isClassNotes ? 'Class Notes' : isWebResearch ? 'Web Research' : 'Both Sources'}:</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {activeSamples.map((item, idx) => (
            <button
              key={idx}
              className="type-tab-btn"
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                borderRadius: '4px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                cursor: 'pointer',
                textAlign: 'left',
              }}
              onClick={() => {
                setQuery(item.text);
                handleSearch(item.text);
              }}
            >
              <span style={{ fontWeight: 700, color: '#1e3a8a', fontFamily: 'monospace', fontSize: '11px' }}>
                {item.course}
              </span>
              <span style={{ color: '#334155' }}>{item.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 3. Error Banner */}
      {error && (
        <div className="banner-alert banner-alert-error" style={{ borderRadius: '6px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* 4. Loading State */}
      {loading && (
        <div
          className="card"
          style={{
            padding: '28px',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            borderRadius: '6px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span className="spinner" style={{ width: '24px', height: '24px' }} />
          <div style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>
            {isClassNotes
              ? 'Searching verified course lecture notes via pgvector HNSW...'
              : isWebResearch
                ? 'Grounding query with live Google Search tool...'
                : 'Combining course curriculum notes and live web evidence...'}
          </div>
          <p style={{ fontSize: '12px', color: '#64748b', margin: 0, maxWidth: '480px' }}>
            Checking topical relevance, verifying citations, and synthesizing a clear answer.
          </p>
        </div>
      )}

      {/* 5. Primary Answer and Results */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Status & Actions Header */}
          <div
            className="card"
            style={{
              padding: '12px 18px',
              backgroundColor: '#ffffff',
              borderRadius: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {isClassNotes && (
                <span className="badge badge-success" style={{ gap: '4px', padding: '3px 8px' }}>
                  <ShieldCheck size={12} /> Grounded in Class Notes
                </span>
              )}
              {isWebResearch && (
                <span
                  style={{
                    backgroundColor: '#eff6ff',
                    color: '#1d4ed8',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Globe size={12} /> Live Web Research
                </span>
              )}
              {isBothSources && (
                <span
                  style={{
                    backgroundColor: '#f5f3ff',
                    color: '#5b21b6',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Layers size={12} /> Course Notes + Web Evidence
                </span>
              )}

              {result.search_status === 'QUOTA_EXHAUSTED' && (
                <span className="badge badge-warning" style={{ gap: '4px' }}>
                  <AlertTriangle size={12} /> Live Web Quota Limited
                </span>
              )}

              {result.search_status === 'NO_RESULTS' && (
                <span className="badge badge-neutral" style={{ gap: '4px' }}>
                  No Relevant Materials Found
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={copyAnswerToClipboard}
                style={{ fontSize: '11.5px', padding: '4px 10px', borderRadius: '4px', gap: '5px' }}
              >
                {copied ? <Check size={12} color="#15803d" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy Answer'}</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={resetSearch}
                style={{ fontSize: '11.5px', padding: '4px 10px', borderRadius: '4px', gap: '5px' }}
              >
                <RotateCcw size={12} />
                <span>New Search</span>
              </button>
            </div>
          </div>

          {/* Quota Exhaustion Notice Banner */}
          {result.search_status === 'QUOTA_EXHAUSTED' && (
            <div
              className="card"
              style={{
                padding: '14px 16px',
                backgroundColor: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '6px',
                color: '#92400e',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
              }}
            >
              <AlertTriangle size={16} color="#d97706" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <strong>Live Search Quota Exhausted:</strong> The live web search API quota for this key has been reached. Class Notes search remains fully active using local vector embeddings.
                <button
                  type="button"
                  onClick={() => {
                    setMode('course_notes');
                    handleSearch(undefined, 'course_notes');
                  }}
                  style={{
                    marginLeft: '8px',
                    textDecoration: 'underline',
                    color: '#1e3a8a',
                    fontWeight: 600,
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  Switch to Class Notes
                </button>
              </div>
            </div>
          )}

          {/* Direct Answer Box (when present) */}
          {result.direct_answer && (
            <div
              className="card"
              style={{
                padding: '16px 20px',
                backgroundColor: '#f8fafc',
                borderLeft: '4px solid #1e3a8a',
                borderRadius: '6px',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#1e3a8a' }}>
                Direct Answer
              </span>
              <p style={{ fontSize: '13.5px', color: '#0f172a', fontWeight: 500, marginTop: '4px', lineHeight: 1.5 }}>
                {result.direct_answer}
              </p>
            </div>
          )}

          {/* Key Points Checklist (when present) */}
          {result.key_findings && result.key_findings.length > 0 && (
            <div className="card" style={{ padding: '18px 20px', borderRadius: '6px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                Key Points
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {result.key_findings.map((kf, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '13px', color: '#1e293b' }}>
                    <Check size={14} color="#15803d" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <span>{kf}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Primary Synthesized Answer Section */}
          <div className="card" style={{ padding: '24px', borderRadius: '6px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', marginBottom: '14px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
              Explanation
            </h3>
            <RenderMarkdownContent content={result.answer} />
          </div>

          {/* 6. Sources Display */}
          {/* Group A: Course Notes Sources */}
          {result.course_sources && result.course_sources.length > 0 && (
            <div className="card" style={{ borderRadius: '6px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h4 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <BookOpen size={15} color="#1e3a8a" />
                  Course Lecture Notes ({result.course_sources.length})
                </h4>
                <span style={{ fontSize: '11px', color: '#64748b' }}>Curriculum Materials</span>
              </div>

              {materialFeedback && (
                <div
                  style={{
                    marginBottom: '12px',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: materialFeedback.isError ? '#fef2f2' : '#f0fdf4',
                    border: `1px solid ${materialFeedback.isError ? '#fecaca' : '#bbf7d0'}`,
                    color: materialFeedback.isError ? '#991b1b' : '#166534',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {materialFeedback.isError ? <AlertCircle size={14} /> : <Check size={14} />}
                    <span>{materialFeedback.text}</span>
                  </div>
                  <button
                    onClick={() => setMaterialFeedback(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
                  >
                    <X size={13} />
                  </button>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '12px' }}>
                {result.course_sources.map((src, index) => {
                  return (
                    <div
                      key={index}
                      style={{
                        padding: '12px 14px',
                        backgroundColor: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                          <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#1e3a8a' }}>
                            {src.material_title}
                          </span>
                        </div>

                        <span style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '8px' }}>
                          Course: <strong>{src.course_title}</strong>
                        </span>

                        <p style={{ fontSize: '12px', color: '#334155', lineHeight: 1.5, marginBottom: '10px' }}>
                          "{src.excerpt}"
                        </p>
                      </div>

                      <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '8px', display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => handleOpenMaterial(src.course_id, src.material_id, src.material_title)}
                          disabled={activeMaterialAction?.materialId === src.material_id}
                          className="btn btn-primary"
                          style={{
                            fontSize: '11px',
                            padding: '3px 8px',
                            borderRadius: '3px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          {activeMaterialAction?.materialId === src.material_id && activeMaterialAction.type === 'open' ? (
                            <Loader2 size={11} className="animate-spin" />
                          ) : (
                            <Eye size={11} />
                          )}
                          <span>Open Material</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleDownloadMaterial(src.course_id, src.material_id, src.material_title)}
                          disabled={activeMaterialAction?.materialId === src.material_id}
                          className="btn btn-secondary"
                          style={{
                            fontSize: '11px',
                            padding: '3px 8px',
                            borderRadius: '3px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            cursor: 'pointer',
                          }}
                          title="Download binary file"
                        >
                          {activeMaterialAction?.materialId === src.material_id && activeMaterialAction.type === 'download' ? (
                            <Loader2 size={11} className="animate-spin" />
                          ) : (
                            <Download size={11} />
                          )}
                          <span>Download</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Group B: Web Research Sources */}
          {result.web_sources && result.web_sources.length > 0 && (
            <div className="card" style={{ borderRadius: '6px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h4 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Globe size={15} color="#1d4ed8" />
                  Live Web Sources ({result.web_sources.length})
                </h4>
                <span style={{ fontSize: '11px', color: '#64748b' }}>Technical Documentation & Publications</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '12px' }}>
                {result.web_sources.map((src, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '12px 14px',
                      backgroundColor: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#0f172a' }}>
                          {src.title || src.domain}
                        </span>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: '3px',
                            backgroundColor: src.source_type === 'ACADEMIC' ? '#f0fdf4' : '#eff6ff',
                            color: src.source_type === 'ACADEMIC' ? '#15803d' : '#1d4ed8',
                          }}
                        >
                          {src.source_type || 'WEB'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px', fontSize: '11px', color: '#64748b' }}>
                        <span>Domain: <strong>{src.domain}</strong></span>
                        {src.publication_date && src.publication_date !== 'Unknown' && (
                          <span>• Date: {src.publication_date}</span>
                        )}
                      </div>

                      <p style={{ fontSize: '12px', color: '#334155', lineHeight: 1.5, marginBottom: '10px' }}>
                        "{src.snippet}"
                      </p>
                    </div>

                    <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary"
                        style={{
                          fontSize: '11px',
                          padding: '3px 8px',
                          borderRadius: '3px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          textDecoration: 'none',
                        }}
                      >
                        <ExternalLink size={11} />
                        <span>Visit Source</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7. Collapsible "How this answer was found" Diagnostics */}
          <div className="card" style={{ padding: '14px 18px', borderRadius: '6px' }}>
            <button
              type="button"
              onClick={() => setShowDiagnostics(!showDiagnostics)}
              style={{
                width: '100%',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: 0,
                fontSize: '12.5px',
                fontWeight: 600,
                color: '#475569',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={14} color="#64748b" />
                <span>How this answer was found</span>
              </div>
              {showDiagnostics ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showDiagnostics && (
              <div
                style={{
                  marginTop: '12px',
                  paddingTop: '12px',
                  borderTop: '1px solid #e2e8f0',
                  fontSize: '12px',
                  color: '#475569',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                }}
              >
                <div>
                  <span style={{ color: '#64748b' }}>Search Mode:</span>{' '}
                  <strong>{result.mode}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>Engine / Model:</span>{' '}
                  <strong>{result.model_used || 'pgvector semantic search'}</strong>
                </div>
                {result.latency_ms !== undefined && (
                  <div>
                    <span style={{ color: '#64748b' }}>Response Time:</span>{' '}
                    <strong>{result.latency_ms} ms</strong>
                  </div>
                )}
                {result.diagnostics?.chunks_evaluated !== undefined && (
                  <div>
                    <span style={{ color: '#64748b' }}>Materials Evaluated:</span>{' '}
                    <strong>{result.diagnostics.chunks_evaluated}</strong>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* In-App Note Preview Modal */}
      {previewTextModal && (
        <div className="modal-overlay" onClick={() => setPreviewTextModal(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="#1e3a8a" />
                <h3>{previewTextModal.title}</h3>
              </div>
              <button
                onClick={() => setPreviewTextModal(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div
                style={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '20px',
                  fontSize: '14px',
                  lineHeight: 1.7,
                  color: '#1e293b',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '60vh',
                  overflowY: 'auto',
                }}
              >
                {previewTextModal.content}
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setPreviewTextModal(null)}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
