import { useEffect, useId, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Search } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { bookPath, Catalog, useResource } from './components';

const recommendationPath = isbn => '/recommendations/' + encodeURIComponent(isbn);
export const emptyChoice = { title: '', book: null };

export function RecommendForm({ choice, setChoice, autoFocus }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const input = useRef(null);
  const id = useId();
  const optionId = index => id + '-option-' + index;
  const query = choice.title.trim();
  const looking = open && !choice.book && query.length >= 2;
  const suggestions = useResource(
    looking ? '/books/search?limit=7&prefer_model=true&q=' + encodeURIComponent(query) : null,
    250,
  );
  const books = suggestions.data ?? [];
  const activeBook = books[activeIndex];

  useEffect(() => {
    if (autoFocus) input.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    if (activeBook) document.getElementById(id + '-option-' + activeIndex)?.scrollIntoView({ block: 'nearest' });
  }, [activeBook, activeIndex, id]);

  function close() {
    setOpen(false);
    setActiveIndex(-1);
  }

  function select(book) {
    setChoice({ title: book.title, book });
    close();
    input.current?.focus({ preventScroll: true });
  }

  function handleKey(e) {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Escape' && looking) {
      e.preventDefault();
      close();
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (choice.book || query.length < 2) return;
      e.preventDefault();
      setOpen(true);
      if (books.length) {
        setActiveIndex(current => {
          if (current < 0) return e.key === 'ArrowDown' ? 0 : books.length - 1;
          return (current + (e.key === 'ArrowDown' ? 1 : -1) + books.length) % books.length;
        });
      }
    }
    if (e.key === 'Enter' && activeBook) {
      e.preventDefault();
      select(activeBook);
    }
  }

  return <form id="recommend-a-book" className="recommend-form" onBlur={e => {
    if (!e.currentTarget.contains(e.relatedTarget)) close();
  }} onSubmit={e => {
    e.preventDefault();
    if (choice.book) navigate(recommendationPath(choice.book.isbn));
  }}>
    <label htmlFor={id + '-input'}>A book you enjoyed</label>
    <div className="recommend-controls">
      <div className="recommend-input-wrap">
        <div className="recommend-input">
          <Search size={19} aria-hidden="true" />
          <input ref={input} id={id + '-input'} type="text" role="combobox" autoComplete="off"
            aria-autocomplete="list" aria-expanded={looking} aria-controls={looking ? id + '-list' : undefined}
            aria-activedescendant={activeBook ? optionId(activeIndex) : undefined}
            placeholder="Search by title…" value={choice.title} maxLength={150}
            onFocus={() => setOpen(true)} onKeyDown={handleKey} onChange={e => {
              setChoice({ title: e.target.value, book: null });
              setOpen(true);
              setActiveIndex(-1);
            }} />
        </div>
        {looking && <div className="recommend-dropdown">
          <ul id={id + '-list'} role="listbox" aria-label="Book suggestions" aria-busy={Boolean(suggestions.loading)}>
            {books.map((book, index) => <li key={book.isbn} id={optionId(index)} role="option"
              aria-selected={activeIndex === index} onPointerDown={e => e.preventDefault()}
              onClick={() => select(book)}>
              <strong>{book.title}</strong><span>{book.author || 'Author unavailable'}</span>
            </li>)}
          </ul>
          {suggestions.loading ? <p role="status">Finding books…</p>
            : suggestions.error ? <p role="alert">{suggestions.error.message}</p>
            : !books.length ? <p role="status">No matches. Try another title.</p>
            : <span className="recommend-sr-only" role="status">{books.length} suggestions available.</span>}
        </div>}
      </div>
      <button className="button" type="submit" disabled={!choice.book}>Find similar books <ArrowRight size={17} /></button>
    </div>
  </form>;
}

export function RecommendationResults({ resetChoice }) {
  const { isbn } = useParams();
  const path = '/books/' + encodeURIComponent(isbn);
  const details = useResource(path);
  const recommendations = useResource(path + '/recommendations');
  const book = recommendations.data?.book ?? details.data;
  const fallback = Boolean(book && (recommendations.error?.status === 404 ||
    (recommendations.data && !recommendations.data.recommendations?.length)));
  const popular = useResource(fallback ? '/books/popular?limit=6&exclude_isbn=' + encodeURIComponent(isbn) : null);
  const heading = useRef(null);

  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
  }, [isbn]);

  return <section className="wrap section page recommendation-page">
    <Link to="/#recommend-a-book" onClick={resetChoice} className="text-link"><ArrowLeft size={17} /> Choose another book</Link>
    <h1 ref={heading} tabIndex={-1}>{book ? <>Because you loved <em>{book.title}</em>…</> : 'Book recommendations'}</h1>
    {book && <p className="recommend-summary">
      <span>{book.author || 'Author unavailable'}</span>
      <Link className="inline-link" to={bookPath(book.isbn)}>View book details</Link>
    </p>}
    {fallback ? <>
      <h2>Popular books to explore</h2>
      <p className="recommend-summary">There are too few shared reader ratings for this book.</p>
      <Catalog resource={popular} bookDestination={recommendationPath} />
    </> : <>
      {book && <p className="recommend-summary">Based on shared ratings from readers.</p>}
      <Catalog resource={{ ...recommendations, data: recommendations.data?.recommendations,
        error: recommendations.error?.status === 404 && details.loading ? undefined :
          recommendations.error?.status === 404 && details.error ? details.error : recommendations.error,
        loading: recommendations.loading || (recommendations.error?.status === 404 && details.loading),
      }} bookDestination={recommendationPath} />
    </>}
  </section>;
}

