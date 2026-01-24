/** Main application component */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header, Footer } from './components/common';
import { TopPage, ComparePage } from './pages';
import { ROUTES } from './utils';
import './styles/global.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main className="container">
          <Routes>
            <Route path={ROUTES.HOME} element={<TopPage />} />
            <Route path={ROUTES.COMPARE} element={<ComparePage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
