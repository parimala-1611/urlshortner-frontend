import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ShortenPage } from './pages/ShortenPage';
import { StatsPage } from './pages/StatsPage';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<ShortenPage />} />
        <Route path="stats" element={<StatsPage />} />
        <Route path="stats/:shortCode" element={<StatsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
