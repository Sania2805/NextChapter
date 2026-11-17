import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Bookmark, BookOpen, Check, Search, ArrowUpRight } from 'lucide-react';
import { motion } from 'motion/react';
import { api } from './api';
import { useSession } from './session';

export const bookPath = isbn => '/books/' + encodeURIComponent(isbn);
export const signIn = path => '/login?next=' + encodeURIComponent(path);
export function useResource(path, delay = 0, revision = 0) {
  const [state, setState] = useState({});
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    const timer = setTimeout(() => api(path, { signal: controller.signal }).then(
      data => { if (!controller.signal.aborted) setState({ path, revision, data }); },
      error => { if (!controller.signal.aborted) setState({ path, revision, error }); },
    ), delay);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [path, delay, revision]);
  return !path ? {} : state.path === path && state.revision === revision ? state : { loading: true };
}

export function Feedback({ children, error = false }) {
  return <p className={'feedback' + (error ? ' error' : '')} role={error ? 'alert' : 'status'}>{children}</p>;
}

export function SearchBox({ initial = '', onChange }) {
  const [value, setValue] = useState(initial);
  const navigate = useNavigate();
  useEffect(() => {
    setValue(initial);
  }, [initial]);
  function submit(e) {
    e.preventDefault();
    navigate('/search' + (value.trim() ? '?q=' + encodeURIComponent(value.trim()) : ''));
  }
  return <form className="search-box" onSubmit={submit} role="search">
    <Search size={19} aria-hidden="true" />
    <input aria-label="Book title" placeholder="Search by book title…" value={value} maxLength={150}
      onChange={e => { setValue(e.target.value); onChange?.(e.target.value); }} />
    <button type="submit">Search</button>
  </form>;
}

export function Cover({ book, eager = false, placeholderWhileLoading = false }) {
  const url = /^https?:\/\//i.test(book.image || '') ? book.image.replace(/^http:/i, 'https:') : '';
  const [failed, setFailed] = useState('');
  const [loaded, setLoaded] = useState('');
  const showImage = url && failed !== url;
  const showPlaceholder = !showImage || (placeholderWhileLoading && loaded !== url);
  return <div className="cover">
    {showImage && <img src={url} alt="" loading={eager ? 'eager' : 'lazy'} referrerPolicy="no-referrer"
      style={showPlaceholder ? { display: 'none' } : undefined}
      onLoad={placeholderWhileLoading ? event => {
        const { naturalWidth, naturalHeight } = event.currentTarget;
        // Some catalog image hosts return a tracking-size placeholder instead of an error.
        if (naturalWidth < 2 || naturalHeight < 2) setFailed(url);
        else setLoaded(url);
      } : undefined} onError={() => setFailed(url)} />}
    {showPlaceholder && <div className="cover-fallback" aria-hidden="true">
      <BookOpen size={25} /><span>{book.title}</span>
    </div>}
  </div>;
}

export function Save({ book, full = false, returnTo, addLabel = 'Save to reading list' }) {
  const { account, checking, items, add, remove, error: listError } = useSession();
  const { pathname, search } = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const row = items?.find(item => item.isbn === book.isbn);
  const title = row ? 'Remove from reading list' : addLabel;
  const body = <>{row ? <Check size={17} /> : <Bookmark size={17} />}{full && (row ? 'Saved · Remove' : title)}</>;
  if (!checking && !account) return <Link className={full ? 'button' : 'icon-button'} aria-label={'Sign in to save ' + book.title} title="Sign in to save" to={signIn(returnTo ?? pathname + search)}>{body}</Link>;
  return <div className="save-control">
    <button type="button" className={full ? 'button' : 'icon-button'} title={title} aria-label={title + ': ' + book.title}
      aria-pressed={Boolean(row)} disabled={busy || !items} onClick={async () => {
        setBusy(true); setError('');
        try {
          if (row) {
            await remove(row.id);
          } else {
            await add(book.isbn);
          }
        }
        catch (e) { setError(e.message); } finally { setBusy(false); }
      }}>{busy && full ? 'Updating…' : body}</button>
    {error && <small role="alert" className="error">{error}</small>}
    {full && listError && <small role="alert" className="error">{listError} <Link to="/reading-list">Open reading list</Link></small>}
  </div>;
}

export function Books({ books, showAvailability = false, bookDestination = bookPath }) {
  return <div className="books">{books.map(book => <motion.article layout="position" key={book.isbn} className="book-card">
    <Link to={bookDestination(book.isbn)} className="book-link">
      <Cover book={book} />
      <h3>{book.title}</h3>
      <p>{book.author || 'Author unavailable'}</p>
      {showAvailability && <small>{book.available ? 'Reader recommendations' : 'Catalog only'}</small>}
    </Link>
    <Save book={book} />
  </motion.article>)}</div>;
}

export function Catalog({ resource, showAvailability, bookDestination }) {
  if (resource.loading) return <Feedback>Loading books…</Feedback>;
  if (resource.error) return <Feedback error>{resource.error.message}</Feedback>;
  if (!resource.data?.length) return <Feedback>No books found. Try a different title.</Feedback>;
  return <Books books={resource.data} showAvailability={showAvailability} bookDestination={bookDestination} />;
}

export function SectionHeading({ caption, title, link }) {
  return <div className="section-heading"><div>{caption && <p className="eyebrow">{caption}</p>}<h2>{title}</h2></div>
    {link && <Link className="text-link" to={link}>View all <ArrowUpRight size={17} /></Link>}</div>;
}


