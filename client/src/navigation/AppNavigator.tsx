import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useSelector } from 'react-redux';
import { RootState } from '../store/store';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { SignupScreen } from '../screens/auth/SignupScreen';
import { RoomsScreen } from '../screens/rooms/RoomsScreen';
import { RootStackParamList } from './types';
import { ChatScreen } from '../screens/chat/ChatScreen';
import { ProfileScreen } from '../screens/main/ProfileScreen';
import { SettingsScreen } from '../screens/main/SettingsScreen';
import { storage } from '../utils/storage';
import { logger } from '../utils/logger';
import { getTraceId } from '../utils/trace';
import { View, Text, ActivityIndicator } from 'react-native';

const Stack = createNativeStackNavigator<RootStackParamList>();

export const AppNavigator = () => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  React.useEffect(() => {
    const checkAuth = async () => {
      const traceId = getTraceId();
      try {
        const token = await storage.getToken();
        logger.info('Auth check completed', { 
          hasToken: !!token, 
          isAuthenticated,
          traceId 
        }, 'navigation');
        setIsLoading(false);
      } catch (error) {
        logger.error('Error checking authentication', { 
          error, 
          traceId 
        }, 'navigation');
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [isAuthenticated]);

  if (isLoading) {
    return (
      <View className="flex-1 items-center justify-center bg-background">
        <ActivityIndicator size="large" color="#007AFF" />
        <Text className="mt-4 text-lg text-grey-2">Loading...</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: '#FFFFFF' },
        }}
      >
        {!isAuthenticated ? (
          // Auth screens
          <>
            <Stack.Screen 
              name="Login" 
              component={LoginScreen}
              options={{ headerShown: false }}
            />
            <Stack.Screen 
              name="Signup" 
              component={SignupScreen}
              options={{ headerShown: false }}
            />
          </>
        ) : (
          // App screens
          <>
            <Stack.Screen 
              name="Rooms" 
              component={RoomsScreen}
              options={{ 
                title: 'My Rooms',
                headerShown: true,
                headerStyle: {
                  backgroundColor: '#FFFFFF',
                },
                headerTintColor: '#000000',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="Chat" 
              component={ChatScreen}
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen 
              name="Profile" 
              component={ProfileScreen}
              options={{
                headerShown: true,
                title: 'Profile',
                headerStyle: {
                  backgroundColor: '#FFFFFF',
                },
                headerTintColor: '#000000',
              }}
            />
            <Stack.Screen 
              name="Settings" 
              component={SettingsScreen}
              options={{
                headerShown: true,
                title: 'Settings',
                headerStyle: {
                  backgroundColor: '#FFFFFF',
                },
                headerTintColor: '#000000',
              }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}; 