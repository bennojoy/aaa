import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Input, Button, Text } from 'react-native-elements';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useDispatch, useSelector } from 'react-redux';
import { RootStackParamList } from '../../navigation/types';
import { SignupData } from '../../types/auth';
import { signupRequest, clearError } from '../../store/authSlice';
import { RootState } from '../../store';
import { validation } from '../../utils/validation';
import { logger } from '../../utils/logger';

type SignupScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Signup'>;

interface ValidationErrors {
  phone_number?: string;
  password?: string;
}

export const SignupScreen = () => {
  const navigation = useNavigation<SignupScreenNavigationProp>();
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state: RootState) => state.auth);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [signupData, setSignupData] = useState<SignupData>({
    phone_number: '',
    password: ''
  });
  const passwordInputRef = useRef<any>(null);

  useEffect(() => {
    // Clear any previous errors when component mounts
    dispatch(clearError());
  }, [dispatch]);

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};
    
    // Validate phone number
    const phoneError = validation.phoneNumber(signupData.phone_number);
    if (phoneError) {
      errors.phone_number = phoneError;
    }

    // Validate password
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
    dispatch(signupRequest(signupData));
  };

  const handleInputChange = (field: keyof SignupData, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }));
    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: undefined }));
    }
    // Clear API error when user starts typing
    if (error) {
      dispatch(clearError());
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.content}>
        <Text h3 style={styles.title}>Create Account</Text>
        
        {error && (
          <Text style={styles.error}>{error}</Text>
        )}

        <Input
          placeholder="Phone Number"
          value={signupData.phone_number}
          onChangeText={(text) => handleInputChange('phone_number', text)}
          autoCapitalize="none"
          keyboardType="phone-pad"
          disabled={loading}
          errorMessage={validationErrors.phone_number}
          returnKeyType="next"
          onSubmitEditing={() => {
            passwordInputRef.current?.focus();
          }}
        />

        <Input
          ref={passwordInputRef}
          placeholder="Password"
          value={signupData.password}
          onChangeText={(text) => handleInputChange('password', text)}
          secureTextEntry
          disabled={loading}
          errorMessage={validationErrors.password}
          returnKeyType="go"
          onSubmitEditing={handleSubmit}
        />

        <Button
          title="Sign Up"
          onPress={handleSubmit}
          loading={loading}
          disabled={loading}
          containerStyle={styles.buttonContainer}
        />

        <Button
          title="Already have an account? Sign in"
          type="clear"
          onPress={() => navigation.navigate('Login')}
          disabled={loading}
        />
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    textAlign: 'center',
    marginBottom: 30,
  },
  error: {
    color: 'red',
    textAlign: 'center',
    marginBottom: 10,
  },
  buttonContainer: {
    marginTop: 20,
    marginBottom: 10,
  },
}); 