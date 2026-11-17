import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { api } from './api';

const Session = createContext(null);
export const useSession = () => useContext(Session);
export function SessionProvider({ children }) {
  const [account, setAccount] = useState(null);
  const [checking, setChecking] = useState(true);
  const [items, setItems] = useState(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const activeAccount = useRef(null);
  function setUser(user) {
    activeAccount.current = user;
    setItems(null);
    setError('');
    setAccount(user);
  }

  useEffect(() => {
    const controller = new AbortController();
    api('/auth/me', { signal: controller.signal }).then(setUser).catch(e => {
      if (e.name !== 'AbortError' && e.status !== 401) setError(e.message);
    }).finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    setError('');
    api('/reading-list', { signal: controller.signal }).then(rows => {
      if (!controller.signal.aborted && activeAccount.current === account) setItems(rows);
    }).catch(e => {
      if (controller.signal.aborted || activeAccount.current !== account) return;
      if (e.status === 401) setUser(null);
      setError(e.message);
    });
    return () => controller.abort();
  }, [account, revision]);

  async function mutate(path, method, body) {
    const owner = activeAccount.current;
    try {
      const row = await api(path, { method, body });
      if (activeAccount.current === owner) {
        setItems(previous => method === 'POST' ? [row, ...previous] :
          method === 'DELETE' ? previous.filter(item => path !== '/reading-list/' + item.id) :
          previous.map(item => item.id === row.id ? row : item));
      }
    } catch (e) {
      if (activeAccount.current === owner) {
        if (e.status === 401) { setUser(null); setError(e.message); }
        if (e.status === 409 || e.status === 404) setRevision(r => r + 1);
      }
      throw e;
    }
  }

  const value = {
    account, checking, items, error,
    refresh: () => setRevision(r => r + 1),
    authenticate: async (kind, body) => setUser(await api('/auth/' + kind, { method: 'POST', body })),
    logout: async () => { await api('/auth/logout', { method: 'POST' }); setUser(null); },
    add: isbn => mutate('/reading-list', 'POST', { isbn }),
    remove: id => mutate('/reading-list/' + id, 'DELETE'),
    update: (id, reading_status) => mutate('/reading-list/' + id, 'PATCH', { reading_status }),
  };
  return <Session.Provider value={value}>{children}</Session.Provider>;
}
