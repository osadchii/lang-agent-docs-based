/**
 * Main App Component
 * Root component that wraps the entire application
 */

import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import './App.css';

function App() {
    return <RouterProvider router={router} />;
}

export default App;
