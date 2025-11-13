/**
 * Home Page (Placeholder)
 * Main landing page for the Mini App
 */

import { useTelegram } from '../../hooks/useTelegram';
import './HomePage.css';

export const HomePage = () => {
  const { user, platform, colorScheme, isReady } = useTelegram();

  if (!isReady) {
    return (
      <div className="home-page loading">
        <div className="loader"></div>
        <p>Загрузка...</p>
      </div>
    );
  }

  return (
    <div className="home-page">
      <div className="hero">
        <div className="gradient-circle"></div>
        <h1 className="title">Lang Agent</h1>
        <p className="subtitle">Учите языки с ИИ-преподавателем</p>
      </div>

      <div className="user-info">
        <div className="info-card">
          <h2>Привет, {user?.first_name || 'Пользователь'}! 👋</h2>
          <p className="welcome-text">
            Добро пожаловать в Lang Agent — вашего личного ИИ-преподавателя для изучения языков.
          </p>
        </div>

        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Платформа:</span>
            <span className="info-value">{platform}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Тема:</span>
            <span className="info-value">{colorScheme}</span>
          </div>
          {user?.username && (
            <div className="info-item">
              <span className="info-label">Username:</span>
              <span className="info-value">@{user.username}</span>
            </div>
          )}
        </div>
      </div>

      <div className="features">
        <h3 className="features-title">Возможности</h3>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h4>Диалог с ИИ</h4>
            <p>Практикуйте язык в диалоге с умным преподавателем</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎴</div>
            <h4>Карточки</h4>
            <p>Запоминайте новые слова и выражения</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <h4>Упражнения</h4>
            <p>Отрабатывайте грамматику и письмо</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h4>Группы</h4>
            <p>Учитесь вместе с друзьями</p>
          </div>
        </div>
      </div>

      <div className="coming-soon">
        <p className="coming-soon-text">
          🚀 <strong>В разработке</strong>
        </p>
        <p className="coming-soon-description">
          Полная функциональность будет доступна в следующих обновлениях
        </p>
      </div>
    </div>
  );
};
