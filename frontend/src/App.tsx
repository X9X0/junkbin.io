import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/layout/Layout';
import ScrollToTop from './components/ScrollToTop';
import ErrorBoundary from './components/ErrorBoundary';
import SuspenseFallback from './components/SuspenseFallback';

const Home = lazy(() => import('./pages/Home'));
const Products = lazy(() => import('./pages/Products'));
const ProductDetail = lazy(() => import('./pages/ProductDetail'));
const Components = lazy(() => import('./pages/Components'));
const ComponentDetail = lazy(() => import('./pages/ComponentDetail'));
const Submit = lazy(() => import('./pages/Submit'));
const Schematics = lazy(() => import('./pages/Schematics'));
const Profile = lazy(() => import('./pages/Profile'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const PasswordReset = lazy(() => import('./pages/PasswordReset'));
const PasswordResetConfirm = lazy(() => import('./pages/PasswordResetConfirm'));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'));
const Moderation = lazy(() => import('./pages/Moderation'));
const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));
const Community = lazy(() => import('./pages/Community'));
const SwapShop = lazy(() => import('./pages/SwapShop'));
const Messages = lazy(() => import('./pages/Messages'));
const MessageThread = lazy(() => import('./pages/MessageThread'));
const NewConversation = lazy(() => import('./pages/NewConversation'));
const UserProfile = lazy(() => import('./pages/UserProfile'));
const Guidelines = lazy(() => import('./pages/Guidelines'));
const Docs = lazy(() => import('./pages/Docs'));
const News = lazy(() => import('./pages/News'));
const MyJunkbin = lazy(() => import('./pages/MyJunkbin'));
const MySubmissions = lazy(() => import('./pages/MySubmissions'));
const Recipes = lazy(() => import('./pages/Recipes'));
const RecipeDetail = lazy(() => import('./pages/RecipeDetail'));
const SubmitRecipe = lazy(() => import('./pages/SubmitRecipe'));
const Buildable = lazy(() => import('./pages/Buildable'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Search = lazy(() => import('./pages/Search'));
const GitHubCallback = lazy(() => import('./pages/GitHubCallback'));
const About = lazy(() => import('./pages/About'));
const Contact = lazy(() => import('./pages/Contact'));
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
          <ScrollToTop />
          <ErrorBoundary>
            <Suspense fallback={<SuspenseFallback />}>
            <Routes>
              <Route path="auth/github/callback" element={<GitHubCallback />} />
              <Route path="/" element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="products" element={<Products />} />
                <Route path="products/:id" element={<ProductDetail />} />
                <Route path="components" element={<Components />} />
                <Route path="components/:id/products" element={<ComponentDetail />} />
                <Route path="schematics" element={<Schematics />} />
                <Route path="search" element={<Search />} />
                <Route path="submit" element={<Submit />} />
                <Route path="leaderboard" element={<Navigate to="/community" replace />} />
                <Route path="community" element={<Community />} />
                <Route path="swap" element={<SwapShop />} />
                <Route path="users/:id" element={<UserProfile />} />
                <Route path="messages" element={<Messages />} />
                <Route path="messages/new" element={<NewConversation />} />
                <Route path="messages/:conversationId" element={<MessageThread />} />
                <Route path="recipes/submit" element={<SubmitRecipe />} />
                <Route path="recipes/:id" element={<RecipeDetail />} />
                <Route path="recipes" element={<Recipes />} />
                <Route path="buildable" element={<Buildable />} />
                <Route path="my-junkbin" element={<MyJunkbin />} />
                <Route path="my-submissions" element={<MySubmissions />} />
                <Route path="about" element={<About />} />
                <Route path="contact" element={<Contact />} />
                <Route path="guidelines" element={<Guidelines />} />
                <Route path="docs" element={<Docs />} />
                <Route path="news" element={<News />} />
                <Route path="moderation" element={<Moderation />} />
                <Route path="analytics" element={<AnalyticsDashboard />} />
                <Route path="profile" element={<Profile />} />
                <Route path="login" element={<Login />} />
                <Route path="register" element={<Register />} />
                <Route path="reset-password" element={<PasswordReset />} />
                <Route path="reset-password/:uid/:token" element={<PasswordResetConfirm />} />
                <Route path="verify-email/:token" element={<VerifyEmail />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
            </Suspense>
          </ErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
