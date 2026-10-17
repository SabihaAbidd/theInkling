import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  ArrowDownRight,
  ArrowUpRight,
  Bookmark,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Download,
  ExternalLink,
  Leaf,
  LoaderCircle,
  LogOut,
  Newspaper,
  Printer,
  RefreshCw,
  Search,
  Settings2,
  Sun,
  X,
} from "lucide-react";
import "./index.css";

const TOKEN_KEY = "asme_token";
const USER_KEY = "asme_user";
const TOPIC_GROUPS = [
  {
    title: "The world and public life",
    topics: ["world", "politics", "society", "education"],
  },
  { title: "Business and money", topics: ["business", "economy", "finance"] },
  {
    title: "Science and technology",
    topics: ["science", "technology", "health", "space", "ai"],
  },
  {
    title: "People and planet",
    topics: ["climate", "environment", "culture", "arts", "books", "film", "music"],
  },
  { title: "Life and leisure", topics: ["sports", "food", "travel", "lifestyle"] },
];

function savedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [user, setUser] = useState(savedUser);
  const [checking, setChecking] = useState(Boolean(token));
  const [sessionMessage, setSessionMessage] = useState("");

  useEffect(() => {
    if (!token) return undefined;
    let active = true;
    api("/api/auth/me", { token })
      .then((currentUser) => {
        if (!active) return;
        localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
        setUser(currentUser);
        setChecking(false);
      })
      .catch((error) => {
        if (!active) return;
        if (error.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setToken("");
          setUser(null);
          setSessionMessage("Your session ended. Sign in to continue.");
        }
        setChecking(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  function finishAuth(data) {
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
    setSessionMessage("");
  }

  function signOut() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken("");
    setUser(null);
  }

  if (checking)
    return (
      <main className="auth-page">
        <div className="loading-mark" role="status">
          <LoaderCircle size={18} className="spin" />
          Checking your account
        </div>
      </main>
    );
  if (user && token) return <ReaderApp user={user} token={token} onSignOut={signOut} />;

  return <AuthScreen message={sessionMessage} onAuth={finishAuth} />;
}

function AuthScreen({ message, onAuth }) {
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState(message || "");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setFieldErrors({});
    setNotice("");
    if (pending) return;
    const errors = {};
    if (isRegister && !name.trim()) {
      errors.name = "Enter your name to create an account.";
    }
    if (!email.trim()) {
      errors.email = "Enter your email address.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = "Enter a valid email address.";
    }
    if (!password) {
      errors.password = "Enter your password.";
    } else if (password.length < 6 || password.length > 128) {
      errors.password = "Use a password between 6 and 128 characters.";
    }
    if (Object.keys(errors).length) {
      setFieldErrors(errors);
      setError("Review the highlighted fields and try again.");
      window.requestAnimationFrame(() => document.getElementById(Object.keys(errors)[0])?.focus());
      return;
    }

    setPending(true);
    try {
      const result = await api("/api/auth/" + (isRegister ? "register" : "login"), {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), email: email.trim(), password }),
      });
      onAuth(result);
    } catch (requestError) {
      setError(
        requestError.status === 400 && isRegister
          ? "We couldn't create this account. Check the details or sign in."
          : requestError.message,
      );
    } finally {
      setPending(false);
    }
  }

  function changeMode(nextMode) {
    setError("");
    setFieldErrors({});
    setNotice("");
    setIsRegister(nextMode === "register");
  }

  function updateField(field, value, setter) {
    setter(value);
    setFieldErrors((current) => ({ ...current, [field]: "" }));
  }

  return (
    <main className="auth-page">
      <div className="auth-topline">
        <BrandMark />
        <span className="auth-top-note">A daily paper, made for you</span>
      </div>
      <div className="auth-layout">
        <section className="auth-intro">
          <div className="issue-stamp">
            <Sun size={14} />
            <span>YOUR MORNING EDITION</span>
          </div>
          <h1>A clearer start to the day.</h1>
          <p>
            Choose what matters to you. The Inkling brings together a personal selection of
            reporting, research, and ideas from around the world.
          </p>
          <div className="auth-proof">
            <span>
              <Leaf size={16} /> Chosen around your interests
            </span>
            <span>
              <ExternalLink size={15} /> Always linked to the source
            </span>
          </div>
        </section>
        <section className="auth-panel" aria-labelledby="auth-title">
          <p className="eyebrow">READER ACCOUNT</p>
          <h2 id="auth-title">{isRegister ? "Make it yours" : "Welcome back"}</h2>
          <p className="auth-panel-copy">
            {isRegister
              ? "Create an account to save your topics and daily editions."
              : "Sign in to open today's paper and your archive."}
          </p>
          {notice && (
            <div className="notice notice-info" role="status">
              {notice}
            </div>
          )}
          {error && (
            <div className="notice notice-error" role="alert" id="auth-error">
              {error}
            </div>
          )}
          <form className="form-stack" onSubmit={submit} noValidate>
            {isRegister && (
              <label className="field">
                <span>Your name</span>
                <input
                  id="name"
                  autoComplete="name"
                  maxLength={80}
                  value={name}
                  onChange={(event) => updateField("name", event.target.value, setName)}
                  aria-invalid={Boolean(fieldErrors.name)}
                  aria-describedby={fieldErrors.name ? "name-error" : undefined}
                />
                {fieldErrors.name && (
                  <small className="field-error" id="name-error">
                    {fieldErrors.name}
                  </small>
                )}
              </label>
            )}
            <label className="field">
              <span>Email address</span>
              <input
                id="email"
                autoComplete="email"
                type="email"
                maxLength={254}
                value={email}
                onChange={(event) => updateField("email", event.target.value, setEmail)}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email && (
                <small className="field-error" id="email-error">
                  {fieldErrors.email}
                </small>
              )}
            </label>
            <div className="field">
              <label htmlFor="password">Password</label>
              <div className="password-control">
                <input
                  id="password"
                  autoComplete={isRegister ? "new-password" : "current-password"}
                  type={showPassword ? "text" : "password"}
                  maxLength={128}
                  value={password}
                  onChange={(event) => updateField("password", event.target.value, setPassword)}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={
                    fieldErrors.password
                      ? "password-error"
                      : isRegister
                        ? "password-hint"
                        : undefined
                  }
                />
                <button
                  type="button"
                  aria-pressed={showPassword}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              {fieldErrors.password ? (
                <small className="field-error" id="password-error">
                  {fieldErrors.password}
                </small>
              ) : (
                isRegister && <small id="password-hint">Use at least 6 characters.</small>
              )}
            </div>
            <button className="button button-primary button-wide" disabled={pending} type="submit">
              {pending ? "Opening your paper..." : isRegister ? "Create account" : "Sign in"}
            </button>
          </form>
          <p className="auth-switch">
            {isRegister ? "Already have an account?" : "New to The Inkling?"}
            <button type="button" onClick={() => changeMode(isRegister ? "login" : "register")}>
              {isRegister ? "Sign in" : "Create an account"}
            </button>
          </p>
        </section>
      </div>
      <footer className="auth-footer">Independent sources. A more considered morning.</footer>
    </main>
  );
}

function ReaderApp({ user, token, onSignOut }) {
  const initialTopics = user.preferences?.topics;
  const [page, setPage] = useState(
    Array.isArray(initialTopics) && initialTopics.length ? "today" : "topics",
  );
  const [preferences, setPreferences] = useState({
    topics: initialTopics || [],
    keywords: user.preferences?.keywords || [],
    excluded_keywords: user.preferences?.excluded_keywords || [],
    preferred_sources: user.preferences?.preferred_sources || [],
    top_n: user.preferences?.top_n || 10,
    use_llm: user.preferences?.use_llm ?? true,
  });
  const [topicOptions, setTopicOptions] = useState([]);
  const [today, setToday] = useState(null);
  const [selectedEdition, setSelectedEdition] = useState(null);
  const [archive, setArchive] = useState([]);
  const [archiveLoaded, setArchiveLoaded] = useState(false);
  const [archiveRefresh, setArchiveRefresh] = useState(0);
  const [archiveQuery, setArchiveQuery] = useState("");
  const [pagePending, setPagePending] = useState(false);
  const [todayPending, setTodayPending] = useState(true);
  const [savePending, setSavePending] = useState(false);
  const [pdfPending, setPdfPending] = useState(false);
  const [pageError, setPageError] = useState("");
  const [banner, setBanner] = useState(null);
  const [retryFeedback, setRetryFeedback] = useState(null);
  const [savedIds, setSavedIds] = useState(() => new Set());
  const [hiddenIds, setHiddenIds] = useState(() => new Set());
  const headingRef = useRef(null);

  const loadToday = useCallback(async () => {
    try {
      const result = await api("/api/papers/today", { token });
      setToday(result.edition);
      setPageError("");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setTodayPending(false);
    }
  }, [token]);

  useEffect(() => {
    let active = true;
    api("/api/preferences/paper", { token })
      .then((result) => {
        if (!active) return;
        setTopicOptions(result.topics || []);
        const saved = result.preferences || {};
        setPreferences((current) => ({
          ...current,
          ...saved,
          topics: saved.topics || current.topics,
        }));
      })
      .catch((error) => {
        if (active) setBanner({ tone: "error", text: error.message });
      });
    const todayTimer = window.setTimeout(loadToday, 0);
    return () => {
      active = false;
      window.clearTimeout(todayTimer);
    };
  }, [token, loadToday]);

  useEffect(() => {
    if (!today || !["queued", "running"].includes(today.status)) return undefined;
    const timer = window.setInterval(() => {
      if (!document.hidden) loadToday();
    }, 3500);
    return () => window.clearInterval(timer);
  }, [today, loadToday]);

  useEffect(() => {
    headingRef.current?.focus({ preventScroll: true });
  }, [page]);

  useEffect(() => {
    if (page !== "archive") return undefined;
    let active = true;
    const archiveTimer = window.setTimeout(() => {
      setPagePending(true);
      api("/api/papers?limit=100", { token })
        .then((result) => {
          if (active) {
            setArchive(result.editions || []);
            setPageError("");
          }
        })
        .catch((error) => {
          if (active) setPageError(error.message);
        })
        .finally(() => {
          if (active) {
            setArchiveLoaded(true);
            setPagePending(false);
          }
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(archiveTimer);
    };
  }, [page, token, archiveRefresh]);

  const visibleArchive = useMemo(() => {
    const query = archiveQuery.trim().toLocaleLowerCase();
    if (!query) return archive;
    return archive.filter((edition) =>
      (edition.articles || []).some((article) =>
        (article.title || "").toLocaleLowerCase().includes(query),
      ),
    );
  }, [archive, archiveQuery]);

  async function createPaper() {
    if (pagePending) return;
    setPageError("");
    setPagePending(true);
    try {
      const result = await api("/api/papers", { method: "POST", token });
      setToday(result);
      setSelectedEdition(null);
      setPage("today");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setPagePending(false);
    }
  }

  async function saveTopics(event) {
    event.preventDefault();
    if (savePending) return;
    setPageError("");
    setSavePending(true);
    try {
      const result = await api("/api/preferences/paper", {
        method: "PUT",
        token,
        body: JSON.stringify(preferences),
      });
      setPreferences(result.preferences);
      setBanner({ tone: "success", text: "Your topics are saved." });
      setPage("today");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setSavePending(false);
    }
  }

  async function openArchiveEdition(editionId) {
    setPagePending(true);
    setPageError("");
    try {
      const result = await api("/api/papers/" + editionId, { token });
      setSelectedEdition(result.edition);
      setPage("today");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setPagePending(false);
    }
  }

  async function downloadPaperPdf(edition) {
    if (!edition?.id || pdfPending) return;
    setPdfPending(true);
    setBanner(null);
    try {
      const file = await apiBlob(`/api/papers/${edition.id}/pdf`, token);
      const objectUrl = window.URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `the-inkling-${edition.date}.pdf`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
      setBanner({ tone: "success", text: "Your edition PDF is ready." });
    } catch (error) {
      setBanner({ tone: "error", text: error.message });
    } finally {
      setPdfPending(false);
    }
  }

  async function submitFeedback(article, action, retry = true) {
    const edition = selectedEdition || today;
    if (!edition || !article.id) return false;
    try {
      await api("/api/papers/" + edition.id + "/feedback", {
        method: "POST",
        token,
        headers: {
          "Idempotency-Key": window.crypto?.randomUUID?.() || String(Date.now()) + "-" + article.id,
        },
        body: JSON.stringify({ news_item_id: article.id, action }),
      });
      if (action === "saved") {
        setSavedIds((current) => new Set(current).add(article.id));
        setBanner({ tone: "success", text: "Story saved to your reading signals." });
      }
      if (action === "skipped" || action === "dismissed") {
        setHiddenIds((current) => new Set(current).add(article.id));
        setBanner({ tone: "success", text: "We'll use that to shape future papers." });
      }
      setRetryFeedback(null);
      return true;
    } catch (error) {
      setBanner({ tone: "error", text: error.message });
      if (retry) setRetryFeedback({ article, action });
      return false;
    }
  }

  function openOriginal(event, article) {
    event.preventDefault();
    window.open(article.url, "_blank", "noopener,noreferrer");
    submitFeedback(article, "opened", false);
  }

  function destination(nextPage) {
    setPage(nextPage);
    setPageError("");
    if (nextPage === "today") setSelectedEdition(null);
  }

  const activeEdition = selectedEdition || today;
  const pageTitle =
    page === "today"
      ? selectedEdition
        ? "From your archive"
        : "Today's paper"
      : page === "archive"
        ? "Your archive"
        : "Your topics";

  return (
    <div className="reader-shell">
      <aside className="reader-spine" aria-label="The Inkling">
        <BrandMark />
        <div className="spine-note">A PAPER OF YOUR OWN</div>
        <nav className="primary-nav" aria-label="Main navigation">
          <NavItem active={page === "today"} onClick={() => destination("today")} icon={Newspaper}>
            Today
          </NavItem>
          <NavItem
            active={page === "archive"}
            onClick={() => destination("archive")}
            icon={Archive}
          >
            Archive
          </NavItem>
          <NavItem
            active={page === "topics"}
            onClick={() => destination("topics")}
            icon={Settings2}
          >
            My topics
          </NavItem>
        </nav>
        <div className="spine-bottom">
          <div className="reader-identity">
            <span className="reader-avatar" aria-hidden="true">
              {user.name?.slice(0, 1).toUpperCase() || "R"}
            </span>
            <span className="reader-name">{user.name || "Reader"}</span>
          </div>
          <button className="spine-signout" type="button" onClick={onSignOut}>
            <LogOut size={15} />
            <span>Sign out</span>
          </button>
          <p className="spine-footer">Independent reading, assembled daily.</p>
        </div>
      </aside>

      <div className="reader-main">
        <header className="paper-topbar">
          <div className="mobile-brand">
            <BrandMark compact />
          </div>
          <span className="topbar-kicker">A personal morning paper</span>
          <div className="topbar-date">
            <Sun size={15} />
            <span>{formatToday()}</span>
          </div>
        </header>
        <main className="paper-content">
          <div className="page-heading-row">
            <div>
              <p className="eyebrow">THE INKLING / PERSONAL EDITION</p>
              <h1 ref={headingRef} tabIndex={-1}>
                {pageTitle}
              </h1>
            </div>
            {page === "today" && (
              <button
                className="button button-outline build-button"
                type="button"
                onClick={selectedEdition ? () => setSelectedEdition(null) : createPaper}
                disabled={pagePending || (today?.status === "ready" && !selectedEdition)}
              >
                {pagePending ? (
                  <LoaderCircle className="spin" size={16} />
                ) : selectedEdition ? (
                  <Newspaper size={15} />
                ) : (
                  <RefreshCw size={15} />
                )}
                {selectedEdition
                  ? "Return to today"
                  : today?.status === "ready"
                    ? "Today's edition is ready"
                    : "Build today's paper"}
              </button>
            )}
          </div>

          {banner && (
            <div
              className={"notice notice-" + banner.tone}
              role={banner.tone === "error" ? "alert" : "status"}
            >
              <span>{banner.text}</span>
              {retryFeedback && (
                <button
                  type="button"
                  className="notice-action"
                  onClick={() => submitFeedback(retryFeedback.article, retryFeedback.action)}
                >
                  Retry
                </button>
              )}
              <button
                className="notice-close"
                type="button"
                aria-label="Dismiss message"
                onClick={() => setBanner(null)}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {pageError && (
            <div className="notice notice-error" role="alert">
              <CircleAlert size={17} />
              <span>{pageError}</span>
              <button
                className="notice-action"
                type="button"
                onClick={() => {
                  if (page === "archive") {
                    setArchiveLoaded(false);
                    setArchiveRefresh((current) => current + 1);
                  } else {
                    loadToday();
                  }
                }}
              >
                Retry
              </button>
            </div>
          )}

          {page === "today" && (
            <TodayPage
              edition={activeEdition}
              isLoading={todayPending && !activeEdition}
              isBuilding={pagePending}
              topics={preferences.topics || []}
              onCreate={createPaper}
              onOpenOriginal={openOriginal}
              onFeedback={submitFeedback}
              onDownload={downloadPaperPdf}
              downloadPending={pdfPending}
              savedIds={savedIds}
              hiddenIds={hiddenIds}
            />
          )}
          {page === "archive" && (
            <ArchivePage
              editions={visibleArchive}
              query={archiveQuery}
              onQueryChange={setArchiveQuery}
              pending={pagePending || !archiveLoaded}
              onOpen={openArchiveEdition}
            />
          )}
          {page === "topics" && (
            <TopicsPage
              preferences={preferences}
              setPreferences={setPreferences}
              options={topicOptions}
              pending={savePending}
              onSave={saveTopics}
            />
          )}
        </main>
        <footer className="paper-footer">
          <span>THE INKLING</span>
          <span>Independent sources, in one considered edition.</span>
        </footer>
      </div>

      <nav className="mobile-nav" aria-label="Main navigation">
        <NavItem active={page === "today"} onClick={() => destination("today")} icon={Newspaper}>
          Today
        </NavItem>
        <NavItem active={page === "archive"} onClick={() => destination("archive")} icon={Archive}>
          Archive
        </NavItem>
        <NavItem active={page === "topics"} onClick={() => destination("topics")} icon={Settings2}>
          Topics
        </NavItem>
      </nav>
    </div>
  );
}

function TodayPage({
  edition,
  isLoading,
  isBuilding,
  topics,
  onCreate,
  onOpenOriginal,
  onFeedback,
  onDownload,
  downloadPending,
  savedIds,
  hiddenIds,
}) {
  if (isLoading)
    return (
      <div className="paper-state" role="status">
        <LoaderCircle className="spin" size={18} />
        Looking for today's edition
      </div>
    );
  if (!edition)
    return (
      <section className="empty-paper">
        <div className="issue-stamp">
          <Sun size={14} />
          <span>FRESH FROM YOUR DESK</span>
        </div>
        <h2>A good morning starts with what matters to you.</h2>
        <p>
          {topics.length
            ? "Your topics are ready. Build a paper and we'll gather the latest stories for you."
            : "Choose a few subjects first. Your paper will grow more personal as you read and respond."}
        </p>
        <button
          className="button button-primary"
          type="button"
          onClick={onCreate}
          disabled={isBuilding}
        >
          {isBuilding ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}
          {isBuilding ? "Preparing today's paper" : "Build today's paper"}
        </button>
      </section>
    );
  if (edition.status === "queued" || edition.status === "running")
    return (
      <section className="progress-paper" aria-live="polite">
        <div className="issue-stamp">
          <Clock3 size={14} />
          <span>{edition.status === "queued" ? "IN THE PRESS QUEUE" : "BEING PUT TOGETHER"}</span>
        </div>
        <h2>Your paper is taking shape.</h2>
        <p>
          We are gathering stories around your interests. You can visit your topics or archive while
          the edition is prepared.
        </p>
        <div className="progress-track">
          <span />
        </div>
        <p className="progress-caption">
          <LoaderCircle className="spin" size={14} />
          This page will update when the edition is ready.
        </p>
      </section>
    );
  if (edition.status === "failed")
    return (
      <section className="empty-paper">
        <div className="issue-stamp issue-stamp-muted">
          <CircleAlert size={14} />
          <span>THE PRESS NEEDS ANOTHER TRY</span>
        </div>
        <h2>Today's paper did not finish.</h2>
        <p>Your topics are saved. Try again in a moment.</p>
        <button className="button button-primary" type="button" onClick={onCreate}>
          Try again
        </button>
      </section>
    );

  const articles = (edition.articles || []).filter((article) => !hiddenIds.has(article.id));
  if (!articles.length)
    return (
      <section className="empty-paper">
        <div className="issue-stamp">
          <Newspaper size={14} />
          <span>EDITION READY</span>
        </div>
        <h2>Today's page is still blank.</h2>
        <p>
          We couldn't find enough recent stories in these subjects yet. Try a wider set of topics
          later.
        </p>
      </section>
    );

  const [lead, ...rest] = articles;
  return (
    <div className="edition">
      <div className="edition-meta">
        <span className="issue-stamp">
          <Sun size={14} />
          <span>YOUR MORNING EDITION</span>
        </span>
        <span className="edition-date">{formatDateOnly(edition.date)}</span>
        <button
          className="button button-outline download-button"
          type="button"
          onClick={() => onDownload(edition)}
          disabled={downloadPending}
          aria-label="Download this newspaper edition as a PDF"
        >
          {downloadPending ? <LoaderCircle className="spin" size={15} /> : <Download size={15} />}
          {downloadPending ? "Preparing PDF" : "Download PDF"}
        </button>
        <button
          className="button button-outline print-button"
          type="button"
          onClick={() => window.print()}
          aria-label="Print this edition or save it as a PDF"
        >
          <Printer size={15} />
          Save as PDF
        </button>
      </div>
      <section className="lead-layout" aria-labelledby="lead-title">
        <article className="lead-story">
          <p className="story-overline">
            <span className="lead-dot" /> LEAD STORY <span className="overline-divider">/</span>{" "}
            {lead.source}
          </p>
          <h2 id="lead-title" className="lead-headline">
            {lead.title}
          </h2>
          <p className="lead-summary">
            {lead.summary || "Open the original story for the full report and details."}
          </p>
          <div className="story-actions">
            <a
              className="button button-primary"
              href={lead.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(event) => onOpenOriginal(event, lead)}
            >
              Read the original <ArrowUpRight size={16} />
            </a>
            <ArticleActions article={lead} onFeedback={onFeedback} saved={savedIds.has(lead.id)} />
          </div>
        </article>
        <aside className="edition-note">
          <div className="note-icon">
            <Leaf size={18} />
          </div>
          <p className="eyebrow">A PAPER OF YOUR OWN</p>
          <p>
            Selected around {topics.slice(0, 3).join(", ") || "the wider world"}. Follow the source
            whenever a story catches your eye.
          </p>
          <div className="note-rule" />
          <span>
            {articles.length} {articles.length === 1 ? "story" : "stories"} in this edition
          </span>
        </aside>
      </section>
      {rest.length > 0 && (
        <section className="latest-section" aria-labelledby="latest-heading">
          <div className="section-rule-heading">
            <h2 id="latest-heading">More from your edition</h2>
            <span>{rest.length} STORIES</span>
          </div>
          <div className="story-grid">
            {rest.map((article, index) => (
              <StoryCard
                key={article.id || article.url}
                article={article}
                index={index + 2}
                onOpenOriginal={onOpenOriginal}
                onFeedback={onFeedback}
                saved={savedIds.has(article.id)}
              />
            ))}
          </div>
        </section>
      )}
      <div className="edition-endnote">
        <span className="endnote-rule" />
        <p>{edition.editorial || "Every story links back to its original publisher."}</p>
        <span className="endnote-rule" />
      </div>
    </div>
  );
}

function StoryCard({ article, index, onOpenOriginal, onFeedback, saved }) {
  return (
    <article className="story-card">
      <div className="story-meta">
        <span>{article.source}</span>
        {article.published_at && (
          <time dateTime={article.published_at}>{formatStoryDate(article.published_at)}</time>
        )}
      </div>
      <h3>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(event) => onOpenOriginal(event, article)}
        >
          {article.title}
        </a>
      </h3>
      <p>{article.summary || "Read the source report for the full story."}</p>
      <div className="story-card-actions">
        <a
          className="text-link"
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(event) => onOpenOriginal(event, article)}
        >
          Read story <ArrowUpRight size={14} />
        </a>
        <ArticleActions article={article} onFeedback={onFeedback} saved={saved} />
      </div>
      <span className="sr-only">Story {index}</span>
    </article>
  );
}

function ArticleActions({ article, onFeedback, saved }) {
  const [pending, setPending] = useState("");
  async function submit(action) {
    if (pending || (saved && action === "saved")) return;
    setPending(action);
    await onFeedback(article, action);
    setPending("");
  }
  return (
    <div className="article-actions">
      <button
        className="quiet-action"
        type="button"
        onClick={() => submit("saved")}
        disabled={pending || saved}
        aria-label={saved ? "Story saved" : "Save story"}
      >
        {pending === "saved" ? (
          <LoaderCircle className="spin" size={15} />
        ) : saved ? (
          <Check size={15} />
        ) : (
          <Bookmark size={15} />
        )}
        <span>{saved ? "Saved" : "Save"}</span>
      </button>
      <button
        className="quiet-action"
        type="button"
        onClick={() => submit("skipped")}
        disabled={Boolean(pending)}
        aria-label="Skip this story"
      >
        {pending === "skipped" ? (
          <LoaderCircle className="spin" size={15} />
        ) : (
          <ArrowDownRight size={15} />
        )}
        <span>Skip</span>
      </button>
    </div>
  );
}

function ArchivePage({ editions, query, onQueryChange, pending, onOpen }) {
  return (
    <section className="archive-page" aria-label="Newspaper archive">
      <div className="archive-intro">
        <p className="eyebrow">KEPT FOR ANOTHER MORNING</p>
        <p>Reopen a past edition and return to the stories you meant to read.</p>
      </div>
      <label className="search-field">
        <Search size={17} />
        <span className="sr-only">Search archived stories</span>
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Find a story in your archive"
          type="search"
        />
        {query && (
          <button type="button" aria-label="Clear archive search" onClick={() => onQueryChange("")}>
            <X size={15} />
          </button>
        )}
      </label>
      {pending && (
        <div className="paper-state" role="status">
          <LoaderCircle className="spin" size={18} />
          Opening your archive
        </div>
      )}
      {!pending && editions.length === 0 && (
        <div className="archive-empty">
          <Archive size={24} />
          <h2>{query ? "No story matches that search." : "Your archive is waiting."}</h2>
          <p>
            {query
              ? "Try another title or clear your search."
              : "When you make your first paper, it will be kept here."}
          </p>
        </div>
      )}
      {editions.length > 0 && (
        <div className="archive-list">
          {editions.map((edition) => (
            <article className="archive-row" key={edition.id}>
              <div className="archive-date">
                <span>{formatMonth(edition.date)}</span>
                <strong>{formatDay(edition.date)}</strong>
                <small>{formatYear(edition.date)}</small>
              </div>
              <div className="archive-edition-copy">
                <p className="eyebrow">
                  {edition.status === "ready" ? "MORNING EDITION" : edition.status.toUpperCase()}
                </p>
                <h2>{edition.title || "The Inkling"}</h2>
                <p>
                  {(edition.articles || []).length} stories <span className="dot-divider">·</span>{" "}
                  {formatWeekday(edition.date)}
                </p>
              </div>
              <button
                className="button button-outline archive-open"
                type="button"
                onClick={() => onOpen(edition.id)}
                disabled={pending || edition.status !== "ready"}
              >
                Open edition <ChevronRight size={16} />
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function TopicsPage({ preferences, setPreferences, options, pending, onSave }) {
  const topicSet = new Set(preferences.topics || []);
  const knownOptions = options.length ? options : TOPIC_GROUPS.flatMap((group) => group.topics);
  const groups = TOPIC_GROUPS.map((group) => ({
    ...group,
    topics: group.topics.filter((topic) => knownOptions.includes(topic)),
  })).filter((group) => group.topics.length);

  function toggle(topic) {
    setPreferences((current) => {
      const selected = new Set(current.topics || []);
      if (selected.has(topic)) selected.delete(topic);
      else selected.add(topic);
      return { ...current, topics: Array.from(selected) };
    });
  }

  return (
    <section className="topics-page">
      <div className="topics-intro">
        <div className="issue-stamp">
          <Settings2 size={14} />
          <span>YOUR EDITORIAL DESK</span>
        </div>
        <h2>Choose what belongs in your morning.</h2>
        <p>
          Pick a few subjects. Your edition will draw from trusted sources and keep every story
          linked to its publisher.
        </p>
      </div>
      <form onSubmit={onSave} noValidate>
        <div className="topic-groups">
          {groups.map((group) => (
            <fieldset className="topic-group" key={group.title}>
              <legend>{group.title}</legend>
              <div className="topic-options">
                {group.topics.map((topic) => (
                  <label
                    className={topicSet.has(topic) ? "topic-option is-selected" : "topic-option"}
                    key={topic}
                  >
                    <input
                      type="checkbox"
                      checked={topicSet.has(topic)}
                      onChange={() => toggle(topic)}
                    />
                    <span>{titleCase(topic)}</span>
                    {topicSet.has(topic) && <Check size={15} aria-hidden="true" />}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="editorial-controls">
          <div>
            <h3>How many stories?</h3>
            <p>Keep your edition short enough for a morning read.</p>
          </div>
          <div className="count-control" role="group" aria-label="Number of stories">
            <button
              type="button"
              aria-label="Show fewer stories"
              disabled={preferences.top_n <= 5}
              onClick={() =>
                setPreferences({ ...preferences, top_n: Math.max(5, preferences.top_n - 1) })
              }
            >
              −
            </button>
            <span>{preferences.top_n}</span>
            <button
              type="button"
              aria-label="Show more stories"
              disabled={preferences.top_n >= 20}
              onClick={() =>
                setPreferences({ ...preferences, top_n: Math.min(20, preferences.top_n + 1) })
              }
            >
              +
            </button>
          </div>
        </div>
        <label className="switch-row">
          <span>
            <strong>Polish headlines and summaries</strong>
            <small>Use the configured language model to edit publisher text carefully.</small>
          </span>
          <input
            type="checkbox"
            checked={preferences.use_llm !== false}
            onChange={(event) => setPreferences({ ...preferences, use_llm: event.target.checked })}
          />
        </label>
        <div className="topic-save-row">
          <p>
            <Leaf size={15} />
            Your choices stay with your account.
          </p>
          <button className="button button-primary" type="submit" disabled={pending}>
            {pending ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}
            {pending ? "Saving topics" : "Save my topics"}
          </button>
        </div>
      </form>
    </section>
  );
}

function NavItem({ active, onClick, icon: Icon, children }) {
  return (
    <button
      className={active ? "nav-item is-active" : "nav-item"}
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
    >
      <Icon size={18} strokeWidth={1.7} aria-hidden="true" />
      <span>{children}</span>
    </button>
  );
}

function BrandMark({ compact = false }) {
  return (
    <div className={compact ? "brand-mark brand-compact" : "brand-mark"}>
      <span className="brand-symbol" aria-hidden="true">
        i
      </span>
      <span className="brand-word">
        the inkling<span className="brand-period">.</span>
      </span>
    </div>
  );
}

function formatToday() {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date());
}
function parseDateOnly(value) {
  const [year, month, day] = String(value || "")
    .split("-")
    .map(Number);
  return year && month && day ? new Date(year, month - 1, day, 12) : new Date();
}
function formatDateOnly(value) {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(parseDateOnly(value));
}
function formatMonth(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short" })
    .format(parseDateOnly(value))
    .toUpperCase();
}
function formatDay(value) {
  return new Intl.DateTimeFormat("en-US", { day: "2-digit" }).format(parseDateOnly(value));
}
function formatYear(value) {
  return new Intl.DateTimeFormat("en-US", { year: "numeric" }).format(parseDateOnly(value));
}
function formatWeekday(value) {
  return new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(parseDateOnly(value));
}
function formatStoryDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}
function titleCase(value) {
  return value.replace(/\b\w/g, (character) => character.toUpperCase());
}
function formatMessage(detail) {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    if (detail.message) return detail.message;
    if (Array.isArray(detail.errors)) return detail.errors.join(" ");
  }
  return "The request could not be completed. Please try again.";
}

async function api(path, options = {}) {
  const { token, headers: extraHeaders = {}, body, ...requestOptions } = options;
  const headers = { Accept: "application/json", ...extraHeaders };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = "Bearer " + token;
  const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

  let response;
  try {
    response = await fetch(apiBase + path, { ...requestOptions, headers, body });
  } catch {
    const error = new Error(
      "The service could not be reached. Check your connection and try again.",
    );
    error.status = 0;
    throw error;
  }

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = formatMessage(result.detail);
    if (response.status === 429) message = "Too many attempts. Please wait a moment and try again.";
    if (response.status >= 500)
      message = "The service is having trouble. Please try again shortly.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return result;
}

async function apiBlob(path, token) {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
  let response;
  try {
    response = await fetch(apiBase + path, {
      headers: { Accept: "application/pdf", Authorization: "Bearer " + token },
    });
  } catch {
    throw new Error("The service could not be reached. Check your connection and try again.");
  }
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    let message = formatMessage(result.detail);
    if (response.status === 429) message = "Too many attempts. Please wait a moment and try again.";
    if (response.status >= 500)
      message = "The service is having trouble. Please try again shortly.";
    throw new Error(message);
  }
  return response.blob();
}

createRoot(document.getElementById("root")).render(<App />);
