export const anonymousSession = { authenticated: false, user: null };

export const authenticatedSession = {
  authenticated: true,
  user: {
    id: 1,
    username: "admin",
    email: "admin@example.test",
    status: "active",
    person: {
      id: 1,
      first_name: "Demo",
      last_name: "Admin",
    },
  },
};
