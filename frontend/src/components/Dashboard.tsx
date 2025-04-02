import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Button,
  TextField,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  InputAdornment,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Link,
  CircularProgress,
} from '@mui/material';
import { Search, YouTube, Instagram, Close, PlayArrow } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface Video {
  id: string;
  title: string;
  thumbnail: string;
  platform: 'youtube' | 'instagram';
  genre: string;
  savedAt: string;
  watchStatus: 'unwatched' | 'watched';
}

const Dashboard = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterGenre, setFilterGenre] = useState('all');
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [playlistUrl, setPlaylistUrl] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch('http://localhost:8000/api/videos', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
      });

      if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setVideos(data);
      } else {
        throw new Error('Failed to fetch videos');
      }
    } catch (error) {
      setError('Failed to load videos');
      console.error('Error fetching videos:', error);
    }
  };

  const handleAddPlaylist = async () => {
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setPlaylistUrl('');
    setError('');
  };

  const handleImportPlaylist = async () => {
    if (!playlistUrl) {
      setError('Please enter a playlist URL');
      return;
    }

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch('http://localhost:8000/api/videos/youtube', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ playlist_url: playlistUrl }),
      });

      if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }

      const data = await response.json();

      if (response.ok) {
        handleCloseDialog();
        await fetchVideos(); // Refresh video list
      } else {
        setError(data.detail || 'Failed to import playlist');
      }
    } catch (error) {
      setError('Failed to import playlist. Please try again.');
      console.error('Error importing playlist:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWatchStatus = async (videoId: string, newStatus: 'watched' | 'unwatched') => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/videos/${videoId}/watch-status`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        setVideos(videos.map(video => 
          video.id === videoId ? { ...video, watchStatus: newStatus } : video
        ));
      } else {
        throw new Error('Failed to update watch status');
      }
    } catch (error) {
      setError('Failed to update watch status');
    }
  };

  const filteredVideos = videos.filter((video) => {
    const matchesSearch = video.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGenre = filterGenre === 'all' || video.genre === filterGenre;
    const matchesPlatform = filterPlatform === 'all' || video.platform === filterPlatform;
    return matchesSearch && matchesGenre && matchesPlatform;
  });

  const genres = Array.from(new Set(videos.map((video) => video.genre)));

  const openVideoLink = (videoId: string, platform: string) => {
    if (platform === 'youtube') {
      window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank');
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={4}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h4" component="h1">
            Your Saved Videos
          </Typography>
          <Button 
            variant="contained" 
            onClick={handleAddPlaylist}
            startIcon={<YouTube />}
          >
            Add YouTube Playlist
          </Button>
        </Box>

        {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search videos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Genre</InputLabel>
              <Select
                value={filterGenre}
                label="Genre"
                onChange={(e) => setFilterGenre(e.target.value)}
              >
                <MenuItem value="all">All Genres</MenuItem>
                {genres.map((genre) => (
                  <MenuItem key={genre} value={genre}>
                    {genre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Platform</InputLabel>
              <Select
                value={filterPlatform}
                label="Platform"
                onChange={(e) => setFilterPlatform(e.target.value)}
              >
                <MenuItem value="all">All Platforms</MenuItem>
                <MenuItem value="youtube">YouTube</MenuItem>
                <MenuItem value="instagram">Instagram</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          {filteredVideos.map((video) => (
            <Grid item key={video.id} xs={12} sm={6} md={4} lg={3}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'scale(1.02)',
                  },
                }}
              >
                <CardMedia
                  component="img"
                  height="140"
                  image={video.thumbnail}
                  alt={video.title}
                  sx={{ cursor: 'pointer' }}
                  onClick={() => openVideoLink(video.id, video.platform)}
                />
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    {video.platform === 'youtube' ? (
                      <YouTube color="error" />
                    ) : (
                      <Instagram color="secondary" />
                    )}
                    <Chip
                      label={video.watchStatus}
                      color={video.watchStatus === 'watched' ? 'success' : 'warning'}
                      size="small"
                      onClick={() => handleWatchStatus(
                        video.id, 
                        video.watchStatus === 'watched' ? 'unwatched' : 'watched'
                      )}
                    />
                  </Box>
                  <Link
                    component="button"
                    variant="subtitle1"
                    onClick={() => openVideoLink(video.id, video.platform)}
                    sx={{ 
                      textAlign: 'left',
                      display: 'block',
                      mb: 1,
                      textDecoration: 'none',
                      '&:hover': { textDecoration: 'underline' }
                    }}
                  >
                    {video.title}
                  </Link>
                  <Typography variant="body2" color="text.secondary">
                    Saved {new Date(video.savedAt).toLocaleDateString()}
                  </Typography>
                  <Chip
                    label={video.genre}
                    color="primary"
                    size="small"
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {filteredVideos.length === 0 && (
          <Typography textAlign="center" color="text.secondary">
            No videos found. Try adjusting your filters or add some videos!
          </Typography>
        )}

        <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
          <DialogTitle>
            Add YouTube Playlist
            <IconButton
              aria-label="close"
              onClick={handleCloseDialog}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent>
            <Box sx={{ mt: 2 }}>
              <TextField
                fullWidth
                label="YouTube Playlist URL"
                placeholder="https://www.youtube.com/playlist?list=..."
                value={playlistUrl}
                onChange={(e) => setPlaylistUrl(e.target.value)}
                error={!!error}
                helperText={error || "Paste the URL of a YouTube playlist"}
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancel</Button>
            <Button
              onClick={handleImportPlaylist}
              variant="contained"
              disabled={isLoading}
              startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
            >
              {isLoading ? 'Importing...' : 'Import Playlist'}
            </Button>
          </DialogActions>
        </Dialog>
      </Stack>
    </Container>
  );
};

export default Dashboard; 