/**
 * Error Page
 * Displayed when something goes wrong or route is not found
 */

import { useRouteError, isRouteErrorResponse, Link } from 'react-router-dom';
import './ErrorPage.css';

export const ErrorPage = () => {
  const error = useRouteError();

  let errorMessage = 'Произошла неизвестная ошибка';
  let errorStatus = '';

  if (isRouteErrorResponse(error)) {
    errorMessage = error.statusText || error.data?.message || 'Страница не найдена';
    errorStatus = error.status.toString();
  } else if (error instanceof Error) {
    errorMessage = error.message;
  }

  return (
    <div className="error-page">
      <div className="error-content">
        <div className="error-icon">⚠️</div>

        {errorStatus && <div className="error-status">{errorStatus}</div>}

        <h1 className="error-title">Упс!</h1>

        <p className="error-message">{errorMessage}</p>

        <div className="error-actions">
          <Link to="/" className="btn-primary">
            Вернуться на главную
          </Link>
        </div>

        {import.meta.env.DEV && error instanceof Error && (
          <details className="error-details">
            <summary>Детали ошибки (dev mode)</summary>
            <pre className="error-stack">{error.stack}</pre>
          </details>
        )}
      </div>
    </div>
  );
};
