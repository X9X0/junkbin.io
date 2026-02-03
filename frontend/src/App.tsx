import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import Components from './pages/Components';
import ComponentDetail from './pages/ComponentDetail';
import Submit from './pages/Submit';
import Schematics from './pages/Schematics';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register';
import PasswordReset from './pages/PasswordReset';
import PasswordResetConfirm from './pages/PasswordResetConfirm';
import VerifyEmail from './pages/VerifyEmail';
import NotFound from './pages/NotFound';
import Search from './pages/Search';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="products" element={<Products />} />
              <Route path="products/:id" element={<ProductDetail />} />
              <Route path="components" element={<Components />} />
              <Route path="components/:id/products" element={<ComponentDetail />} />
              <Route path="schematics" element={<Schematics />} />
              <Route path="search" element={<Search />} />
              <Route path="submit" element={<Submit />} />
              <Route path="profile" element={<Profile />} />
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />
              <Route path="reset-password" element={<PasswordReset />} />
              <Route path="reset-password/:uid/:token" element={<PasswordResetConfirm />} />
              <Route path="verify-email/:uid/:token" element={<VerifyEmail />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
