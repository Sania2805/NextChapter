import { useEffect, useId, useRef, useState } from 'react';
import { ArrowUpRight, RotateCcw, Sparkles, X } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { Link } from 'react-router-dom';
import { api } from './api';
import { bookPath, Cover, Feedback, Save } from './components';

const frameTimes = [0, 80, 160, 250, 350, 470, 610, 780, 990, 1240, 1550, 1920];
const revealTime = 2450;

export function SurpriseMe() {
  const dialog = useRef(null);
  const closeButton = useRef(null);
  const activeSpin = useRef(null);
  const lastPick = useRef(null);
  const reducedMotion = useReducedMotion();
  const headingId = useId();
  const [round, setRound] = useState({ phase: 'idle' });
  const busy = round.phase === 'loading' || round.phase === 'rolling';

  useEffect(() => () => activeSpin.current?.abort(), []);

  async function spin() {
    if (activeSpin.current) return;
    const controller = new AbortController();
    activeSpin.current = controller;
    closeButton.current.focus();
    setRound({ phase: 'loading' });

    try {
      const query = lastPick.current ? '?exclude_isbn=' + encodeURIComponent(lastPick.current) : '';
      const { book, previews } = await api('/books/surprise' + query, { signal: controller.signal });
      if (controller.signal.aborted) return;
      lastPick.current = book.isbn;
      const cards = reducedMotion ? [book] : [...previews, book];

      function reveal() {
        activeSpin.current = null;
        setRound({ phase: 'revealed', book, cards, frame: cards.length - 1 });
      }

      if (reducedMotion || !previews.length) {
        reveal();
        return;
      }

      setRound({ phase: 'rolling', cards, frame: 0 });
      const started = performance.now();
      let step = 0;
      let timer;

      function advance() {
        step += 1;
        if (step === frameTimes.length) {
          reveal();
          return;
        }
        setRound({ phase: 'rolling', cards, frame: step % previews.length });
        queueFrame();
      }

      function queueFrame() {
        const nextTime = frameTimes[step + 1] ?? revealTime;
        timer = setTimeout(advance, Math.max(0, nextTime - (performance.now() - started)));
      }

      controller.signal.addEventListener('abort', () => clearTimeout(timer), { once: true });
      queueFrame();
    } catch (error) {
      if (controller.signal.aborted) return;
      activeSpin.current = null;
      setRound({ phase: 'error', message: error.message });
    }
  }

  function cancelSpin() {
    activeSpin.current?.abort();
    activeSpin.current = null;
    setRound({ phase: 'idle' });
  }

  const visibleBook = round.book;
  return <div className="surprise-entry">
    <button type="button" className="button outline surprise-trigger" aria-haspopup="dialog" onClick={() => {
      dialog.current.showModal();
      void spin();
    }}> Surprise me!</button>

    <dialog ref={dialog} className="surprise-dialog" aria-labelledby={headingId} onCancel={cancelSpin}>
      <div className="surprise-panel">
        <button type="button" ref={closeButton} className="icon-button surprise-close" aria-label="Close surprise picker"
          onClick={() => { cancelSpin(); dialog.current.close(); }}><X size={20} aria-hidden="true" /></button>
        <h2 id={headingId}>Let fate pick your next read.</h2>
        <p className="recommend-sr-only" role="status">
          {busy ? 'Picking a book…' : visibleBook ? 'Your surprise pick is ' + visibleBook.title : ''}
        </p>
        {(busy || visibleBook) && <div className="surprise-stage" aria-hidden="true">
          {round.phase === 'loading' && <span className="surprise-loading">Loading books…</span>}
          {round.cards?.map((book, index) => <div key={book.isbn} className="surprise-frame"
            data-active={index === round.frame} data-winner={visibleBook?.isbn === book.isbn}>
            <motion.div initial={false}
              animate={!reducedMotion && index === round.cards.length - 1 && !visibleBook
                ? { scale: 0.91, y: 9 } : { scale: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 360, damping: 16 }}>
              <Cover book={book} eager placeholderWhileLoading />
            </motion.div>
          </div>)}
        </div>}
        {round.phase === 'error' && <Feedback error>{round.message}</Feedback>}
        {visibleBook && <>
          <div className="surprise-meta">
            <h3>{visibleBook.title}</h3>
            <p>{visibleBook.author || 'Author unavailable'}{visibleBook.year ? ' · ' + visibleBook.year : ''}</p>
            {visibleBook.average_rating != null && <p>
              <strong>{visibleBook.average_rating.toFixed(1)}/10</strong> · {visibleBook.rating_count.toLocaleString()} reader ratings
            </p>}
          </div>
          <div className="surprise-actions">
            <Save key={visibleBook.isbn} book={visibleBook} full returnTo={bookPath(visibleBook.isbn)} addLabel="Add to reading list" />
            <Link className="button outline" to={bookPath(visibleBook.isbn)}>View details <ArrowUpRight size={16} aria-hidden="true" /></Link>
          </div>
        </>}
        {(visibleBook || round.phase === 'error') && <button className="button outline surprise-retry" type="button" onClick={spin}>
          <RotateCcw size={16} aria-hidden="true" /> Try again
        </button>}
      </div>
    </dialog>
  </div>;
}
