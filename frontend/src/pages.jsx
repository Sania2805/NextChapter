import { useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, Bookmark, BookOpen, Compass, LogOut, Menu, Search, TrendingUp, X } from 'lucide-react';
import { motion } from 'motion/react';
import { bookPath, Catalog, Cover, Feedback, Save, SearchBox, SectionHeading, signIn, useResource } from './components';
import { emptyChoice, RecommendForm, RecommendationResults } from './recommendations';
import { useSession } from './session';
import { SurpriseMe } from './surprise';

const navigation = [
  { to: '/', label: 'Discover', icon: Compass },
  { to: '/popular', label: 'Popular books', icon: TrendingUp },
  { to: '/search', label: 'Search catalog', icon: Search },
  { to: '/reading-list', label: 'Reading list', icon: Bookmark },
];

function Brand() {
  return <Link className="brand" to="/">
    <span className="brand-mark"><BookOpen size={22} aria-hidden="true" /></span> NextChapter
  </Link>;
}

function Header() {
  const { account, checking, items, logout } = useSession();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => { setOpen(false); }, [location.key]);

  return <header className="header">
    <div className="nav-head">
      <Brand />
      <button type="button" className="icon-button nav-toggle" aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open} aria-controls="main-nav" onClick={() => setOpen(!open)}>
        {open ? <X size={21} /> : <Menu size={21} />}
      </button>
    </div>
    <div id="main-nav" className={'nav-body' + (open ? ' open' : '')}>
      <nav aria-label="Main navigation">
        {navigation.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'}
          className={to === '/' && location.pathname.startsWith('/recommendations/') ? 'active' : undefined}>
          <Icon size={19} aria-hidden="true" /> {label}
          {to === '/reading-list' && items && <span className="nav-count">{items.length}</span>}
        </NavLink>)}
      </nav>
      <div className="nav-account">
        {!checking && (account ? <>
          <span className="account-name">{account.username}</span>
          <button type="button" className="icon-button" aria-label="Sign out" title="Sign out" disabled={busy}
            onClick={async () => {
              setBusy(true); setError('');
              try { await logout(); navigate('/'); } catch (e) { setError(e.message); } finally { setBusy(false); }
            }}><LogOut size={18} aria-hidden="true" /></button>
        </> : <Link className="button outline" to={signIn(location.pathname + location.search + location.hash)}>Sign in <ArrowRight size={16} /></Link>)}
        {error && <small className="error" role="alert">{error}</small>}
      </div>
    </div>
  </header>;
}

function BookGraphic() {
  return <div className="book-graphic" aria-hidden="true">
    <div className="graphic-book graphic-book-back" />
    <div className="graphic-book graphic-book-front">
      <BookOpen size={64} strokeWidth={1.5} />
      <span className="graphic-lines" />
    </div>
  </div>;
}

function Home({ choice, setChoice }) {
  const popular = useResource('/books/popular?limit=6');
  const { hash } = useLocation();
  return <div className="wrap section">
    <section className="hero" aria-labelledby="recommendation-title">
      <div className="hero-copy">
        <h1 id="recommendation-title">Find your<br /><span>next great read.</span></h1>
        <p className="lede">Start with a book you loved. Get recommendations based on what readers with similar tastes enjoyed.</p>
        <RecommendForm choice={choice} setChoice={setChoice} autoFocus={hash === '#recommend-a-book'} />
        <SurpriseMe />
      </div>
      <BookGraphic />
    </section>
    <section className="home-shelf" aria-label="Popular books">
      <SectionHeading title="Popular books" link="/popular" />
      <Catalog resource={popular} />
    </section>
  </div>;
}

function Popular() {
  const books = useResource('/books/popular?limit=30');
  return <section className="wrap section page">
    <h1>Popular books</h1>
    <p className="lede">Explore reader favorites from the NextChapter catalog.</p>
    <Catalog resource={books} />
  </section>;
}

function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const cleaned = q.trim();
  const books = useResource(cleaned ? '/books/search?limit=30&q=' + encodeURIComponent(cleaned) : null, 300);
  return <section className="wrap section page"><h1>Search catalog</h1>
    <SearchBox initial={q} onChange={value => setParams(value ? { q: value } : {}, { replace: true })} />
    {cleaned ? <div className="results"><h2>Results for “{cleaned}”</h2><Catalog resource={books} showAvailability /></div>
      : <Feedback>Search the catalog by title to find and save books.</Feedback>}
  </section>;
}

function Details() {
  const { isbn } = useParams();
  return <BookDetails key={isbn} isbn={isbn} />;
}

function BookDetails({ isbn }) {
  const path = '/books/' + encodeURIComponent(isbn);
  const details = useResource(path);
  const recs = useResource(details.data?.available ? path + '/recommendations' : null);
  const fallback = Boolean(details.data && (!details.data.available || recs.error?.status === 404));
  const popular = useResource(fallback ? '/books/popular?limit=6&exclude_isbn=' + encodeURIComponent(isbn) : null);
  if (!details.data) return <section className="wrap section page"><Feedback error={Boolean(details.error)}>{details.error?.message || 'Finding this edition…'}</Feedback><Link to="/search">Back to search</Link></section>;
  const book = details.data;
  return <section className="wrap section page"><div className="detail">
    <Cover book={book} eager /><div><p className="eyebrow">From the catalog</p><h1>{book.title}</h1>
    <p className="lede">{book.author || 'Author unavailable'}</p><p className="isbn">ISBN {book.isbn}</p><Save book={book} full /></div></div>
    <div className="results"><SectionHeading caption={fallback ? 'From the popular shelf' : 'Related reading'} title={fallback ? 'Popular books to explore' : 'Books you might love'} />
    {fallback ? <><p className="lede">There are too few shared reader ratings for this title. Explore the popular shelf instead.</p>
      <Catalog resource={popular} /></>
      : <><p className="lede">Based on shared ratings from readers.</p><Catalog resource={{ ...recs, data: recs.data?.recommendations }} /></>}</div>
  </section>;
}

const statuses = { want_to_read: 'Want to read', reading: 'Reading', finished: 'Finished' };

function ListRow({ item }) {
  const { update, remove } = useSession();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(false);
  async function change(action) {
    setBusy(true); setMessage('');
    try { await action(); setError(false); setMessage('Status updated.'); }
    catch (e) { setError(true); setMessage(e.message); }
    finally { setBusy(false); }
  }
  return <motion.li layout="position" className="list-row">
    <Link to={bookPath(item.isbn)} className="list-cover"><Cover book={item.book} /></Link>
    <div><Link to={bookPath(item.isbn)}><h3>{item.book.title}</h3></Link><p>{item.book.author}</p><small>ISBN {item.isbn}</small>
    {message && <small className={error ? 'error' : ''} role={error ? 'alert' : 'status'}>{message}</small>}</div>
    <div className="list-controls"><select aria-label={'Reading status for ' + item.book.title} disabled={busy} value={item.reading_status}
      onChange={e => change(() => update(item.id, e.target.value))}>
      {Object.entries(statuses).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select>
    <button className="button outline" disabled={busy} onClick={() => change(() => remove(item.id))}>Remove</button></div>
  </motion.li>;
}

function ReadingList() {
  const { checking, account, items, error, refresh } = useSession();
  return <section className="wrap section page journal-page"><h1>My reading list</h1>
    <p className="lede">Keep track of the books you want to read, the ones you’re reading, and the ones you’ve finished.</p>
    {error && <Feedback error>{error}</Feedback>}
    {checking ? <Feedback>Checking your session…</Feedback> : !account ? <Link className="button" to={signIn('/reading-list')}>Sign in to see your list</Link>
      : error ? <button className="button" onClick={refresh}>Try again</button>
      : !items ? <Feedback>Loading your reading list…</Feedback>
      : !items.length ? <><Feedback>Your reading list is empty. Save a book to get started.</Feedback><Link className="button" to="/popular">Explore popular books</Link></>
      : <ul className="reading-list">{items.map(item => <ListRow item={item} key={item.id} />)}</ul>}
  </section>;
}

function Auth({ register }) {
  const { authenticate, checking } = useSession();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const next = params.get('next') || '/reading-list';
  const destination = /^\/(?![\/\\])/.test(next) ? next : '/reading-list';
  const authQuery = '?next=' + encodeURIComponent(destination);
  return <section className="auth-wrap">
    <div className="auth-story">
      <Brand />
      <div><h1>Good books.<br /><span>More of them.</span></h1>
        <p className="lede">Discover books based on your favorites and keep track of what you want to read next.</p>
        <BookGraphic />
      </div>
    </div>
    <div className="auth-card">
    <nav className="auth-tabs" aria-label="Account access">
      <NavLink to={'/register' + authQuery}>Create account</NavLink>
      <NavLink to={'/login' + authQuery}>Sign in</NavLink>
    </nav>
    <h2>{register ? 'Create your account' : 'Sign in to NextChapter'}</h2>
    <p className="lede">{register ? 'Create an account to save books and track your reading.' : 'Sign in to pick up where you left off.'}</p>
    <form onSubmit={async e => {
      e.preventDefault(); setError(''); setBusy(true);
      const body = Object.fromEntries(new FormData(e.currentTarget));
      try { await authenticate(register ? 'register' : 'login', body); navigate(destination, { replace: true }); }
      catch (e) { setError(e.message); } finally { setBusy(false); }
    }}>
      {register && <label>Username<input name="username" autoComplete="username" required minLength={2} maxLength={40} /></label>}
      <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
      <label>Password<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 12 : 1} maxLength={128} /></label>
      {register && <small>Use at least 12 characters.</small>}
      {error && <Feedback error>{error}</Feedback>}
      <button className="button" disabled={busy || checking}>{busy ? 'One moment…' : register ? 'Create account' : 'Sign in'}</button>
    </form>
  </div></section>;
}

export function App() {
  const { pathname, hash } = useLocation();
  const [choice, setChoice] = useState(emptyChoice);
  const authPage = /^\/(login|register)\/?$/i.test(pathname);
  useEffect(() => {
    if (!hash || hash === '#recommend-a-book') window.scrollTo(0, 0);
  }, [pathname, hash]);
  return <div className={authPage ? 'auth-shell' : 'app-shell'}>
    <a className="skip" href="#main">Skip to content</a>
    {!authPage && <Header />}
    <main id="main" tabIndex={-1}><Routes>
    <Route path="/" element={<Home choice={choice} setChoice={setChoice} />} />
    <Route path="/recommendations/:isbn" element={<RecommendationResults resetChoice={() => setChoice(emptyChoice)} />} />
    <Route path="/popular" element={<Popular />} /><Route path="/search" element={<SearchPage />} />
    <Route path="/books/:isbn" element={<Details />} /><Route path="/reading-list" element={<ReadingList />} />
    <Route path="/login" element={<Auth key="login" />} /><Route path="/register" element={<Auth key="register" register />} />
    <Route path="*" element={<section className="wrap section page"><Compass /><h1>Page not found</h1><Link to="/">Back to Discover</Link></section>} />
    </Routes></main>
  </div>;
}
