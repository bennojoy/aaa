import React, { useState, useEffect } from 'react';
import { View, KeyboardAvoidingView, Platform, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { Text } from 'react-native-elements';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useDispatch, useSelector } from 'react-redux';
import { RootStackParamList } from '../../navigation/types';
import { LoginCredentials } from '../../types/auth';
import { loginRequest, clearError, clearAuthState } from '../../store/slices/authSlice';
import { RootState } from '../../store/store';
import { validation } from '../../utils/validation';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';

type LoginScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Login'>;

interface ValidationErrors {
  identifier?: string;
  password?: string;
}

interface AuthState {
  loading: boolean;
  error: string | null;
  token: string | null;
  user: {
    id: string;
    name: string;
  } | null;
}

export const LoginScreen = () => {
  const navigation = useNavigation<LoginScreenNavigationProp>();
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state: RootState & { auth: AuthState }) => state.auth);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [credentials, setCredentials] = useState<LoginCredentials>({
    identifier: '',
    password: ''
  });

  useEffect(() => {
    const traceId = getTraceId();
    logger.info('Login screen mounted, clearing auth state', { traceId }, 'auth');
    dispatch(clearAuthState());
    dispatch(clearError());
  }, [dispatch]);

  const validateForm = (): boolean => {
    console.log('Starting form validation');
    const errors: ValidationErrors = {};
    
    // Phone validation
    if (!credentials.identifier) {
      errors.identifier = 'Phone number is required';
    } else {
      const phoneError = validation.phoneNumber(credentials.identifier);
      console.log('Phone validation result:', phoneError);
      if (phoneError) {
        errors.identifier = phoneError;
      }
    }

    // Password validation
    if (!credentials.password) {
      errors.password = 'Password is required';
    } else {
      const passwordError = validation.required(credentials.password);
      console.log('Password validation result:', passwordError);
      if (passwordError) {
        errors.password = passwordError;
      }
    }

    console.log('Final validation errors:', errors);
    setValidationErrors(errors);
    const isValid = Object.keys(errors).length === 0;
    console.log('Form is valid:', isValid);
    return isValid;
  };

  const handleSubmit = () => {
    console.log('Login button pressed');
    console.log('Current credentials:', {
      identifier: credentials.identifier,
      password: credentials.password ? '****' : ''
    });
    
    if (!validateForm()) {
      console.log('Form validation failed. Errors:', validationErrors);
      return;
    }
    
    console.log('Form validation passed, dispatching login request');
    dispatch(loginRequest(credentials));
  };

  const handleInputChange = (field: keyof LoginCredentials, value: string) => {
    console.log(`Input changed for ${field}:`, value);
    setCredentials(prev => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: undefined }));
    }
    if (error) {
      dispatch(clearError());
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1 bg-background"
    >
      <View className="flex-1 px-6 justify-center">
        <Text className="text-3xl font-bold text-center mb-8 text-foreground">
          Welcome Back
        </Text>
        
        {error && (
          <Text className="text-error text-center mb-4">{error}</Text>
        )}

        <View className="mb-4">
          <TextInput
            className="bg-grey-5 px-4 py-3 rounded-lg text-foreground"
            placeholder="Phone Number"
            placeholderTextColor="#86939e"
            value={credentials.identifier}
            onChangeText={(text) => handleInputChange('identifier', text)}
            autoCapitalize="none"
            keyboardType="phone-pad"
            editable={!loading}
          />
          {validationErrors.identifier && (
            <Text className="text-error text-sm mt-1 font-bold">{validationErrors.identifier}</Text>
          )}
        </View>

        <View className="mb-6">
          <TextInput
            className="bg-grey-5 px-4 py-3 rounded-lg text-foreground"
            placeholder="Password"
            placeholderTextColor="#86939e"
            value={credentials.password}
            onChangeText={(text) => handleInputChange('password', text)}
            secureTextEntry
            editable={!loading}
          />
          {validationErrors.password && (
            <Text className="text-error text-sm mt-1 font-bold">{validationErrors.password}</Text>
          )}
        </View>

        {/* Debug display - remove in production */}
        {Object.keys(validationErrors).length > 0 && (
          <View className="mb-4 p-2 bg-red-100 rounded">
            <Text className="text-error text-sm">
              Validation Errors: {JSON.stringify(validationErrors)}
            </Text>
          </View>
        )}

        <TouchableOpacity
          className={`bg-primary py-3 rounded-lg mb-4 ${loading ? 'opacity-50' : ''}`}
          onPress={handleSubmit}
          disabled={loading}
        >
          <Text className="text-white text-center font-semibold text-lg">
            {loading ? 'Logging in...' : 'Login'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          className="py-2"
          onPress={() => navigation.navigate('Signup')}
          disabled={loading}
        >
          <Text className="text-primary text-center">
            Don't have an account? Sign up
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}; 