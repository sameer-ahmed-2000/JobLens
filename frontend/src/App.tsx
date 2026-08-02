import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import Dashboard from './pages/Dashboard';
import CareerWorkspace from './pages/CareerWorkspace';
import { CareerProfile } from './pages/CareerProfile.tsx';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-base flex flex-col font-body text-text-warm antialiased selection:bg-focus-confirm/30 selection:text-text-warm">
          <Header />
          <main className="flex-1 max-w-7xl w-full mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/workspace" element={<CareerWorkspace />} />
              <Route path="/profile" element={<CareerProfile />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}


export default App;
