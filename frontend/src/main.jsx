import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MotionConfig } from 'motion/react';
import { SessionProvider } from './session';
import { App } from './pages';
import './style.css';

createRoot(document.getElementById('root')).render(
  <BrowserRouter><MotionConfig reducedMotion="user"><SessionProvider><App /></SessionProvider></MotionConfig></BrowserRouter>
);
