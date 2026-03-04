import { Github } from 'lucide-react';

const GITHUB_CLIENT_ID = import.meta.env.VITE_GITHUB_CLIENT_ID as string | undefined;

interface GitHubLoginButtonProps {
  text?: 'signin_with' | 'signup_with';
  onSuccess: (code: string) => void;
  onError: (message: string) => void;
}

export default function GitHubLoginButton({
  text = 'signin_with',
  onSuccess,
  onError,
}: GitHubLoginButtonProps) {
  if (!GITHUB_CLIENT_ID) return null;

  const handleClick = () => {
    const callbackUrl = `${window.location.origin}/auth/github/callback`;
    const params = new URLSearchParams({
      client_id: GITHUB_CLIENT_ID,
      redirect_uri: callbackUrl,
      scope: 'user:email',
      state: crypto.randomUUID(),
    });

    const popup = window.open(
      `https://github.com/login/oauth/authorize?${params}`,
      'github-oauth',
      'width=600,height=700,scrollbars=yes,resizable=yes',
    );

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== 'github-oauth-code') return;

      window.removeEventListener('message', handleMessage);
      popup?.close();

      if (event.data.code) {
        onSuccess(event.data.code);
      } else {
        onError(event.data.error || 'GitHub sign-in was cancelled.');
      }
    };

    window.addEventListener('message', handleMessage);

    // Clean up listener if popup is closed without completing
    const pollClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(pollClosed);
        window.removeEventListener('message', handleMessage);
      }
    }, 500);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-600 bg-[#24292f] text-white hover:bg-[#32383f] transition-colors font-mono text-sm"
    >
      <Github className="h-5 w-5" />
      {text === 'signup_with' ? 'Sign up with GitHub' : 'Sign in with GitHub'}
    </button>
  );
}
