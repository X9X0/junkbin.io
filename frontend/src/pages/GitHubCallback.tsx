import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

export default function GitHubCallback() {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const error = searchParams.get('error');

    if (window.opener) {
      window.opener.postMessage(
        { type: 'github-oauth-code', code: code ?? null, error: error ?? null },
        window.location.origin,
      );
    }
    window.close();
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen bg-cyber-black">
      <p className="text-gray-400 font-mono text-sm animate-pulse">AUTHENTICATING...</p>
    </div>
  );
}
