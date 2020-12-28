class Player():
    def __init__(self, userid, rating_mean, rating_std, username=None):
        assert isinstance(userid, int), "Userid should be of type integer"
        assert isinstance(rating_mean, (float, int)), "The rating mean should be of type float"
        assert isinstance(rating_std, (float, int)), "The rating sigma should be of type float"

        self.___userid = userid
        if username is not None:
            self.___username = username
        else:
            self.___username = None
        self.___rating_mean = rating_mean
        self.___rating_std = rating_std
    

    def update_rating(self, mean_delta, std_delta):
        """
        Updates the rating of the player.

        Args:
            mean_delta (float): Change in the mean value of the rating.
            std_delta (float): Change in the standard deviation of the rating.
        
        Returns:
            tuple: (mean_of_the_rating, std_of_the_rating)
        """
        
        self.___rating_mean += mean_delta
        self.___rating_std += std_delta
        return (self.___rating_mean, self.___rating_std)


    def update_username(self, username):
        """
        Updates the username of the player.

        Args:
            username (string): New username of the player.

        Returns:
            string: The new username of the player
        """

        self.___username = username
        return self.___username


    @property
    def userid(self):
        """
        Getter for userid.

        Args:
            None
        
        Returns:
            int: Userid of the player.
        """
        return self.___userid


    @property
    def username(self):
        """
        Getter for username.

        Args:
            None
        
        Returns:
            string: Username of the player.
        """
        return self.___username


    @property
    def rating_mean(self):
        """
        Getter for rating's mean value.

        Args:
            None
        
        Returns:
            float: Player rating's mean value.
        """
        return self.___rating_mean


    @property
    def rating_std(self):
        """
        Getter for rating's std value.

        Args:
            None
        
        Returns:
            float: Player rating's std value.
        """
        return self.___rating_std
