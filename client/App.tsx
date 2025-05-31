import "./global.css";
import React from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor } from './src/store/store';
import { AppNavigator } from './src/navigation/AppNavigator';
import { logger } from './src/utils/logger';
import { loggerConfig } from './src/config/logger';

// Initialize logger with configuration
logger.configure({
  ...loggerConfig,
  environment: process.env.NODE_ENV as 'development' | 'production'
});

export default function App() {
  return (
    <SafeAreaProvider>
      <Provider store={store}>
        <PersistGate loading={null} persistor={persistor}>
          <AppNavigator />
        </PersistGate>
      </Provider>
    </SafeAreaProvider>
  );
} 