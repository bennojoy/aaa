/// <reference types="nativewind/types" />

declare module 'nativewind' {
  import type { ComponentType } from 'react';
  import type { ViewProps, TextProps, ImageProps } from 'react-native';

  export function styled<T extends ComponentType<any>>(
    Component: T,
    options?: { className?: string }
  ): T;

  export function useColorScheme(): 'light' | 'dark';

  export function useColorSchemeValue<T>(light: T, dark: T): T;
} 