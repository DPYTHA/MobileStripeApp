import React from "react";
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar, Platform, View, Text } from 'react-native';
import AppNavigator from './src/navigation/AppNavigator';
import { UserProvider } from './src/context/UserContext';


export default function App() {
  if (Platform.OS === 'web') {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f5f5f5' }}>
        <Text style={{ fontSize: 20, fontWeight: 'bold', color: 'red' }}>
          🚫 Accès refusé : Application non disponible sur PC !
        </Text>
      </View>
    );
  }

  return (
   <UserProvider>
    <NavigationContainer>
      <StatusBar barStyle="dark-content" backgroundColor="orange" />
    
     <AppNavigator/>
    
    </NavigationContainer>
    </UserProvider>
  
  );
};
