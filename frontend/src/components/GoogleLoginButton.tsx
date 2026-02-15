import { useEffect, useRef, useState } from 'react';

interface GoogleLoginButtonProps {
  onSuccess: (credential: string) => void;
  onError: (message: string) => void;
  text?: 'signin_with' | 'signup_with' | 'continue_with';
}

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export default function GoogleLoginButton({
  onSuccess,
  onError,
  text = 'signin_with',
}: GoogleLoginButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  // Poll for the GSI library (loaded async)
  useEffect(() => {
    if (!CLIENT_ID) return;

    if (typeof google !== 'undefined' && google.accounts?.id) {
      setReady(true);
      return;
    }

    const interval = setInterval(() => {
      if (typeof google !== 'undefined' && google.accounts?.id) {
        setReady(true);
        clearInterval(interval);
      }
    }, 200);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!ready || !buttonRef.current || !CLIENT_ID) return;

    google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (response) => {
        if (response.credential) {
          onSuccess(response.credential);
        } else {
          onError('Google sign-in was cancelled');
        }
      },
    });

    google.accounts.id.renderButton(buttonRef.current, {
      type: 'standard',
      theme: 'filled_black',
      size: 'large',
      text,
      shape: 'rectangular',
      width: buttonRef.current.offsetWidth,
    });
  }, [ready, text, onSuccess, onError]);

  // Don't render anything if Google OAuth is not configured
  if (!CLIENT_ID) return null;

  return <div ref={buttonRef} className="w-full flex justify-center" />;
}
