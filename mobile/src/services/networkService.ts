import NetInfo from '@react-native-community/netinfo';

export const networkService = {
  /**
   * Check if device is currently connected to internet
   */
  isConnected: async (): Promise<boolean> => {
    const state = await NetInfo.fetch();
    return state.isConnected === true && state.isInternetReachable === true;
  },

  /**
   * Subscribe to network state changes
   * @param callback Function to call when network state changes
   * @returns Unsubscribe function
   */
  subscribe: (callback: (isConnected: boolean) => void) => {
    return NetInfo.addEventListener(state => {
      const connected = state.isConnected === true && state.isInternetReachable === true;
      callback(connected);
    });
  },
};
