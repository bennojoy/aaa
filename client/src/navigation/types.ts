import { User } from '../types/auth';

export type RootStackParamList = {
  Login: undefined;
  Signup: undefined;
  Rooms: undefined;
  Chat: {
    roomId: string;
    roomType: 'user' | 'assistant';
    roomName: string;
  };
  Profile: {
    userId: string;
  };
  Settings: undefined;
}; 