import React, { useState, useEffect, useRef } from 'react';
import { View, KeyboardAvoidingView, Platform, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { Text } from 'react-native-elements';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useDispatch, useSelector } from 'react-redux';
import { RootStackParamList } from '../../navigation/types';
import { SignupData } from '../../types/auth';
import { signupRequest, clearError, clearAuthState } from '../../store/slices/authSlice';
import { RootState } from '../../store/store';
import { validation } from '../../utils/validation';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';

type SignupScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Signup'>;

interface ValidationErrors {
  phone_number?: string;
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

export const SignupScreen = () => {
  const navigation = useNavigation<SignupScreenNavigationProp>();
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state: RootState & { auth: AuthState }) => state.auth);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [signupData, setSignupData] = useState<SignupData>({
    phone_number: '',
    password: ''
  });
  const [showSuccess, setShowSuccess] = useState(false);
  const passwordInputRef = useRef<TextInput>(null);

  useEffect(() => {
    const traceId = getTraceId();
    logger.info('Signup screen mounted, clearing auth state', { traceId }, 'auth');
    dispatch(clearAuthState());
    dispatch(clearError());
  }, [dispatch]);

  useEffect(() => {
    if (!loading && !error && showSuccess) {
      const timer = setTimeout(() => {
        navigation.navigate('Login');
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [loading, error, showSuccess, navigation]);

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};
    
    const phoneError = validation.phoneNumber(signupData.phone_number);
    if (phoneError) {
      errors.phone_number = phoneError;
    }

    const passwordError = validation.required(signupData.password);
    if (passwordError) {
      errors.password = passwordError;
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = () => {
    logger.debug('Signup form submitted', { signupData }, 'auth');
    if (!validateForm()) {
      logger.debug('Signup form validation failed', { validationErrors }, 'auth');
      return;
    }
    logger.debug('Dispatching signup request', { signupData }, 'auth');
    setShowSuccess(true);
    dispatch(signupRequest(signupData));
  };

  const handleInputChange = (field: keyof SignupData, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }));
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
          Create Account
        </Text>
        
        {error && (
          <Text className="text-error text-center mb-4">{error}</Text>
        )}

        {showSuccess && !error && !loading && (
          <Text className="text-success text-center mb-4">
            Account created successfully! Redirecting to login...
          </Text>
        )}

        <View className="mb-4">
          <TextInput
            className="bg-grey-5 px-4 py-3 rounded-lg text-foreground"
            placeholder="Phone Number"
            placeholderTextColor="#86939e"
            value={signupData.phone_number}
            onChangeText={(text) => handleInputChange('phone_number', text)}
            autoCapitalize="none"
            keyboardType="phone-pad"
            editable={!loading}
            returnKeyType="next"
            onSubmitEditing={() => {
              passwordInputRef.current?.focus();
            }}
          />
          {validationErrors.phone_number && (
            <Text className="text-error text-sm mt-1">{validationErrors.phone_number}</Text>
          )}
        </View>

        <View className="mb-6">
          <TextInput
            ref={passwordInputRef}
            className="bg-grey-5 px-4 py-3 rounded-lg text-foreground"
            placeholder="Password"
            placeholderTextColor="#86939e"
            value={signupData.password}
            onChangeText={(text) => handleInputChange('password', text)}
            secureTextEntry
            editable={!loading}
            returnKeyType="go"
            onSubmitEditing={handleSubmit}
          />
          {validationErrors.password && (
            <Text className="text-error text-sm mt-1">{validationErrors.password}</Text>
          )}
        </View>

        <TouchableOpacity
          className={`bg-primary py-3 rounded-lg mb-4 ${loading ? 'opacity-50' : ''}`}
          onPress={handleSubmit}
          disabled={loading}
        >
          <Text className="text-white text-center font-semibold text-lg">
            {loading ? 'Creating Account...' : 'Sign Up'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          className="py-2"
          onPress={() => navigation.navigate('Login')}
          disabled={loading}
        >
          <Text className="text-primary text-center">
            Already have an account? Sign in
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}; 