import React, { useState, useEffect } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Input, Button, Text } from 'react-native-elements';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useDispatch, useSelector } from 'react-redux';
import { RootStackParamList } from '../../navigation/types';
import { LoginCredentials } from '../../types/auth';
import { loginRequest, clearError } from '../../store/authSlice';
import { RootState } from '../../store';
import { validation } from '../../utils/validation';

type LoginScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Login'>;

interface ValidationErrors {
  identifier?: string;
  password?: string;
}

export const LoginScreen = () => {
  const navigation = useNavigation<LoginScreenNavigationProp>();
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state: RootState) => state.auth);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [credentials, setCredentials] = useState<LoginCredentials>({
    identifier: '',
    password: ''
  });

  useEffect(() => {
    // Clear any previous errors when component mounts
    dispatch(clearError());
  }, [dispatch]);

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};
    
    // Validate phone number
    const phoneError = validation.phoneNumber(credentials.identifier);
    if (phoneError) {
      errors.identifier = phoneError;
    }

    // Validate password
    const passwordError = validation.required(credentials.password);
    if (passwordError) {
      errors.password = passwordError;
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = () => {
    if (!validateForm()) {
      return;
    }
    dispatch(loginRequest(credentials));
  };

  const handleInputChange = (field: keyof LoginCredentials, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
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
        <Text h3 style={styles.title}>Welcome Back</Text>
        
        {error && (
          <Text style={styles.error}>{error}</Text>
        )}

        <Input
          placeholder="Phone Number"
          value={credentials.identifier}
          onChangeText={(text) => handleInputChange('identifier', text)}
          autoCapitalize="none"
          keyboardType="phone-pad"
          disabled={loading}
          errorMessage={validationErrors.identifier}
          returnKeyType="next"
          onSubmitEditing={() => {
            // Focus the password input
            const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
            if (passwordInput) {
              passwordInput.focus();
            }
          }}
        />

        <Input
          placeholder="Password"
          value={credentials.password}
          onChangeText={(text) => handleInputChange('password', text)}
          secureTextEntry
          disabled={loading}
          errorMessage={validationErrors.password}
          returnKeyType="go"
          onSubmitEditing={handleSubmit}
        />

        <Button
          title="Login"
          onPress={handleSubmit}
          loading={loading}
          disabled={loading}
          containerStyle={styles.buttonContainer}
        />

        <Button
          title="Don't have an account? Sign up"
          type="clear"
          onPress={() => navigation.navigate('Signup')}
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